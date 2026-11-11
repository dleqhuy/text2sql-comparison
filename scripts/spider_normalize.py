"""Conservative, schema-aware syntax adaptation for Spider's restricted parser.

Projection labels may be removed only at query boundaries where no other SQL
scope consumes them. Values, column positions, predicates and join types stay.
No gold SQL is used in this transformation.
"""

import re
from collections import Counter

import sqlglot
from common import SQLITE_KEYWORDS
from sqlglot import exp
from sqlglot.dialects.sqlite import SQLite
from sqlglot.optimizer.scope import Scope, traverse_scope


class SpiderSQLite(SQLite):
    class Generator(SQLite.Generator):
        def neq_sql(self, expression):
            return self.binary(expression, "!=")

        def not_sql(self, expression):
            child = expression.this
            if isinstance(child, exp.Is):
                return self.binary(child, "IS NOT")
            if isinstance(child, (exp.In, exp.Like, exp.Between)):
                left = self.sql(child, "this")
                rendered = self.sql(child)
                return left + " NOT" + rendered[len(left) :]
            return super().not_sql(expression)


def nearest_select(node):
    return node.find_ancestor(exp.Select)


def source_columns(source, schema):
    if isinstance(source, exp.Table):
        return set(schema.get(source.name.lower(), []))
    if isinstance(source, Scope):
        return {name.lower() for name in source.expression.named_selects}
    return set()


def resolved_identifier(node, scope_by_select, schema):
    col = node.parent
    if not isinstance(col, exp.Column) or col.this is not node:
        return True
    scope = scope_by_select.get(id(nearest_select(col)))
    while scope is not None:
        sources = {name.lower(): source for name, source in scope.sources.items()}
        if col.table:
            if col.table.lower() in sources:
                return col.name.lower() in source_columns(
                    sources[col.table.lower()], schema
                )
        else:
            if any(
                col.name.lower() in source_columns(source, schema)
                for source in sources.values()
            ):
                return True
            # Projection aliases can be resolved by clauses, but not siblings.
            if isinstance(scope.expression, exp.Select):
                clause = col
                while (
                    clause.parent is not scope.expression and clause.parent is not None
                ):
                    clause = clause.parent
                if clause not in scope.expression.expressions and any(
                    alias.alias.lower() == col.name.lower()
                    for alias in scope.expression.expressions
                    if isinstance(alias, exp.Alias)
                ):
                    return True
        scope = scope.parent
    return False


def normalize(sql, schema):
    statements = sqlglot.parse(sql, read="sqlite")
    if len(statements) != 1 or not isinstance(statements[0], exp.Query):
        raise ValueError("Expected a single SELECT query")
    tree = statements[0]
    rules = Counter()
    scopes = list(traverse_scope(tree))
    scope_by_select = {id(scope.expression): scope for scope in scopes}
    known_names = {name.lower() for name in schema}
    known_names.update(col.lower() for cols in schema.values() for col in cols)
    known_names.update(node.name.lower() for node in tree.find_all(exp.TableAlias))
    known_names.update(node.alias.lower() for node in tree.find_all(exp.Alias))

    # Only unquote simple schema/alias identifiers, never quoted string literals.
    # Unknown double-quoted names retain SQLite's double-quoted-string behavior.
    for node in tree.find_all(exp.Identifier):
        if (
            node.args.get("quoted")
            and node.name.lower() in known_names
            and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", node.name)
            and node.name.upper() not in SQLITE_KEYWORDS
            and resolved_identifier(node, scope_by_select, schema)
        ):
            node.set("quoted", False)
            rules["unquote_identifier"] += 1

    # Spider has a global alias map. Give physical-table aliases unique names,
    # resolving local and correlated column references before changing sources.
    renames, tables = {}, []
    reserved = {node.name.lower() for node in tree.find_all(exp.Identifier)}
    for scope in scopes:
        for name, (_, source) in scope.selected_sources.items():
            if isinstance(source, exp.Table) and source.alias:
                candidate = f"spider_t{len(tables) + 1}"
                while (
                    candidate in reserved and candidate != source.alias.lower()
                ) or candidate in schema:
                    candidate += "_"
                reserved.add(candidate)
                renames[(id(scope), name.lower())] = candidate
                tables.append((source, candidate))
    for col in tree.find_all(exp.Column):
        if not col.table:
            continue
        scope = scope_by_select.get(id(nearest_select(col)))
        while scope is not None:
            sources = {name.lower(): source for name, source in scope.sources.items()}
            if col.table.lower() in sources:
                name = renames.get((id(scope), col.table.lower()))
                if name:
                    col.set("table", exp.to_identifier(name))
                break
            scope = scope.parent
    for source, name in tables:
        source.set("alias", exp.TableAlias(this=exp.to_identifier(name)))
        rules["explicit_unique_table_alias"] += 1

    for select in tree.find_all(exp.Select):
        scope = scope_by_select.get(id(select))
        # Derived tables and CTEs export their projection labels to other scopes.
        if scope is None or scope.is_derived_table or scope.is_cte:
            continue
        aliases = [node for node in select.expressions if isinstance(node, exp.Alias)]
        alias_counts = Counter(node.alias.lower() for node in aliases)
        source_columns = set()
        unknown_source = False
        for source in scope.sources.values():
            if isinstance(source, exp.Table):
                cols = schema.get(source.name.lower())
                if cols is None:
                    unknown_source = True
                else:
                    source_columns.update(c.lower() for c in cols)
            elif isinstance(source, Scope):
                source_columns.update(
                    name.lower() for name in source.expression.named_selects
                )
        for alias in aliases:
            name = alias.alias.lower()
            if alias_counts[name] != 1 or unknown_source:
                continue
            # Keep volatile/unknown functions: expanding an alias can evaluate
            # its expression again. Aggregates here are deterministic.
            if any(
                not isinstance(func, (exp.Count, exp.Sum, exp.Min, exp.Max, exp.Avg))
                for func in alias.this.find_all(exp.Func)
            ):
                continue
            references = [
                c
                for c in select.find_all(exp.Column)
                if not c.table and c.name.lower() == name
            ]
            if any(nearest_select(c) is not select for c in references):
                continue
            replacements = []
            unsafe = False
            for col in references:
                if col.find_ancestor(exp.Alias) is not None:
                    # Sibling projection aliases cannot refer to each other in SQLite.
                    continue
                clause = col
                while clause.parent is not select and clause.parent is not None:
                    clause = clause.parent
                if clause in select.expressions:
                    continue
                if isinstance(clause, exp.Order) and isinstance(
                    col.parent, exp.Ordered
                ):
                    replacements.append(col)
                elif name not in source_columns:
                    # GROUP/HAVING/WHERE/ON prefer real columns over aliases.
                    replacements.append(col)
                elif isinstance(clause, exp.Order):
                    # Alias/column resolution within ORDER expressions is subtle.
                    unsafe = True
            if unsafe:
                continue
            for col in replacements:
                value = alias.this.copy()
                if isinstance(value, exp.Binary):
                    value = exp.Paren(this=value)
                col.replace(value)
                rules["expand_projection_alias_reference"] += 1
            alias.replace(alias.this.copy())
            rules["remove_projection_label"] += 1

    for join in tree.find_all(exp.Join):
        if join.args.get("kind") == "INNER":
            join.set("kind", None)
            rules["inner_join_keyword"] += 1
    for node in list(tree.find_all(exp.Paren)):
        if isinstance(node.this, (exp.Column, exp.Literal)):
            node.replace(node.this.copy())
            rules["atomic_parentheses"] += 1
    rules["not_equal_operator"] = sum(1 for _ in tree.find_all(exp.NEQ))
    return tree.sql(dialect=SpiderSQLite), dict(rules)
