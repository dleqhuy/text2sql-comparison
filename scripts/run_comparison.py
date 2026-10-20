"""Run DIN-SQL, MAC-SQL and DAIL-SQL on full Spider dev or its first N examples."""

import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

from common import ROOT, read_json

METHODS = ("few_shot", "mac_sql", "dail_sql")
REPOS = {
    "few_shot": "Few-shot-NL2SQL-with-prompting",
    "mac_sql": "MAC-SQL",
    "dail_sql": "DAIL-SQL",
}


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--count", type=int, help="First N dev examples; default: all")
    result.add_argument("--methods", nargs="+", choices=METHODS, default=list(METHODS))
    result.add_argument(
        "--spider-data", type=Path, default=ROOT / "downloads/spider_data"
    )
    result.add_argument(
        "--data-dir", type=Path, help="Default: data/dev_full or data/smokeN"
    )
    result.add_argument(
        "--output", type=Path, help="Default: results/full_dev or results/smokeN"
    )
    result.add_argument(
        "--evaluate-only",
        action="store_true",
        help="Normalize and score existing raw output",
    )
    result.add_argument(
        "--dry-run",
        action="store_true",
        help="Print steps without writing files or calling LLMs",
    )
    return result


class Comparison:
    def __init__(self, args):
        if args.count is not None and args.count < 1:
            raise ValueError("--count must be positive")
        if len(set(args.methods)) != len(args.methods):
            raise ValueError("--methods must not contain duplicates")
        self.args = args
        self.source = args.spider_data.resolve()
        dev = read_json(self.source / "dev.json")
        self.count = len(dev) if args.count is None else args.count
        if not 0 < self.count <= len(dev):
            raise ValueError(f"--count must be between 1 and {len(dev)}")
        name = "full_dev" if args.count is None else f"smoke{self.count}"
        self.data = (
            args.data_dir
            or ROOT / "data" / ("dev_full" if args.count is None else name)
        ).resolve()
        self.output = (args.output or ROOT / "results" / name).resolve()
        self.env = dict(os.environ)
        self.env.setdefault("NLTK_DATA", "/private/tmp/text2sql-nltk")
        self.env["PYTHONUNBUFFERED"] = "1"

    def raw(self, method):
        suffix = "jsonl" if method == "mac_sql" else "txt"
        return self.output / "raw" / f"{method}.{suffix}"

    def validate(self):
        expected = [f"dev_{i:04d}" for i in range(self.count)]
        if (self.data / "subset.json").exists():
            if read_json(self.data / "subset.json") != expected:
                raise ValueError(f"Dataset selection differs from --count: {self.data}")
        if self.args.evaluate_only:
            for name in ("examples.json", "tables.json", "subset.json"):
                if not (self.data / name).is_file():
                    raise FileNotFoundError(self.data / name)
            for method in self.args.methods:
                if not self.raw(method).is_file():
                    raise FileNotFoundError(self.raw(method))
            return
        # Never overwrite inference or silently reuse an earlier MAC-SQL run.
        for method in self.args.methods:
            if not self.args.dry_run and self.raw(method).exists():
                raise FileExistsError(
                    f"Existing output: {self.raw(method)}; choose another --output or --evaluate-only"
                )
        if (
            not self.args.dry_run
            and (self.output / "dail_work").exists()
            and "dail_sql" in self.args.methods
        ):
            raise FileExistsError(
                f"Existing DAIL workspace: {self.output / 'dail_work'}; choose another --output"
            )
        if not self.args.dry_run:
            for key in ("LLM_MODEL", "LLM_API_KEY", "LLM_BASE_URL"):
                if not self.env.get(key):
                    raise ValueError(f"Set {key} by sourcing .env first")
            for method in self.args.methods:
                python = ROOT.parent / REPOS[method] / ".venv/bin/python"
                if not python.is_file():
                    raise FileNotFoundError(python)
            if "dail_sql" in self.args.methods:
                for name in (
                    "train_spider.json",
                    "train_others.json",
                    "train_gold.sql",
                ):
                    if not (self.source / name).is_file():
                        raise FileNotFoundError(self.source / name)

    def command(self, argv, cwd=ROOT, log=None):
        argv = list(map(str, argv))
        print(f"[{cwd}] {shlex.join(argv)}", flush=True)
        if self.args.dry_run:
            return
        if log is None:
            subprocess.run(argv, cwd=cwd, env=self.env, check=True)
        else:
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open("w") as stream:
                try:
                    subprocess.run(
                        argv,
                        cwd=cwd,
                        env=self.env,
                        stdin=subprocess.DEVNULL,
                        stdout=stream,
                        stderr=subprocess.STDOUT,
                        check=True,
                    )
                except subprocess.CalledProcessError as error:
                    raise RuntimeError(f"Step failed; see {log}") from error

    def copy(self, source, target):
        print(f"Copy {source} -> {target}", flush=True)
        if not self.args.dry_run:
            shutil.copy2(source, target)

    def dail(self):
        repo = ROOT.parent / REPOS["dail_sql"]
        work = self.output / "dail_work"
        stage = work / "dataset/spider"
        java = self.env.setdefault(
            "JAVA_HOME",
            str(repo / "third_party/java11/jdk-11.0.32.1+1-jre/Contents/Home"),
        )
        self.env["PATH"] = (
            str(Path(java) / "bin") + os.pathsep + self.env.get("PATH", "")
        )
        self.env.setdefault(
            "CORENLP_HOME", str(repo / "third_party/stanford-corenlp-full-2018-10-05")
        )
        self.env.setdefault("HF_HOME", str(repo / ".cache/huggingface"))
        self.env.setdefault(
            "SENTENCE_TRANSFORMERS_HOME", str(repo / ".cache/sentence-transformers")
        )
        self.env.update(TOKENIZERS_PARALLELISM="false", DAIL_CACHE_CELL_MATCHES="1")
        links = {
            "dev.json": self.data / "dev.json",
            "tables.json": self.data / "tables.json",
            "dev_gold.sql": self.data / "gold.txt",
            "database": self.source / "database",
        }
        links.update(
            {
                name: self.source / name
                for name in ("train_spider.json", "train_others.json", "train_gold.sql")
            }
        )
        for name, source in links.items():
            if not self.args.dry_run:
                if not source.exists():
                    raise FileNotFoundError(source)
                stage.mkdir(parents=True, exist_ok=True)
                (stage / name).symlink_to(source, target_is_directory=source.is_dir())
        print(f"DAIL stage: {stage} ({self.count} examples)", flush=True)
        python = repo / ".venv/bin/python"

        def command(script, *argv, log):
            self.command(
                [python, repo / script, *argv], work, self.output / "raw" / log
            )

        command("data_preprocess.py", "--tokenize-only", log="dail_preprocess.log")
        common = [
            "--data_type",
            "spider",
            "--split",
            "test",
            "--tokenizer",
            "gpt-3.5-turbo",
            "--max_seq_len",
            "4096",
            "--prompt_repr",
            "SQL",
            "--k_shot",
            "9",
            "--example_type",
            "QA",
        ]
        model = (
            self.env.get("LLM_MODEL", "<LLM_MODEL>")
            .replace("/", "_")
            .replace("\\", "_")
        )
        preliminary = self.output / "raw/dail_preliminary.txt"
        for phase, selector in (
            ("preliminary", "EUCDISQUESTIONMASK"),
            ("final", "EUCDISMASKPRESKLSIMTHR"),
        ):
            args = [*common, "--selector_type", selector]
            if phase == "final":
                args += ["--pre_test_result", preliminary]
            command("generate_question.py", *args, log=f"dail_{phase}_prompts.log")
            prompts = (
                work
                / f"dataset/process/SPIDER-TEST_SQL_9-SHOT_{selector}_QA-EXAMPLE_CTX-200_ANS-4096"
            )
            if not self.args.dry_run:
                if (
                    len(read_json(prompts / "questions.json")["questions"])
                    != self.count
                ):
                    raise ValueError("DAIL prompt count differs from dataset")
            command(
                "ask_llm.py",
                "--n",
                "1",
                "--end_index",
                self.count,
                "--question",
                prompts,
                log=f"dail_{phase}_inference.log",
            )
            result = prompts / f"RESULTS_MODEL-{model}.txt"
            if (
                not self.args.dry_run
                and len(result.read_text().splitlines()) != self.count
            ):
                raise ValueError("DAIL output count differs from dataset")
            self.copy(
                result, preliminary if phase == "preliminary" else self.raw("dail_sql")
            )

    def run(self):
        self.validate()
        print(
            f"Examples: {self.count}; data: {self.data}; output: {self.output}",
            flush=True,
        )
        if not self.args.evaluate_only:
            args = [
                sys.executable,
                ROOT / "scripts/prepare_data.py",
                "--spider-data",
                self.source,
                "--output",
                self.data,
            ]
            if self.args.count is not None:
                args += ["--count", self.count]
            self.command(args)
            if not self.args.dry_run:
                (self.output / "raw").mkdir(parents=True, exist_ok=True)
            for method in self.args.methods:
                repo = ROOT.parent / REPOS[method]
                python = repo / ".venv/bin/python"
                if method == "few_shot":
                    self.command(
                        [
                            python,
                            "DIN-SQL.py",
                            "--dataset",
                            str(self.data) + "/",
                            "--output",
                            self.raw(method),
                        ],
                        repo,
                        self.output / "raw/few_shot.log",
                    )
                elif method == "mac_sql":
                    self.command(
                        [
                            python,
                            "run.py",
                            "--dataset_name",
                            "spider",
                            "--dataset_mode",
                            "dev",
                            "--input_file",
                            self.data / "dev.json",
                            "--db_path",
                            os.path.relpath(self.source / "database", repo),
                            "--tables_json_path",
                            self.data / "tables.json",
                            "--output_file",
                            self.raw(method),
                            "--log_file",
                            self.output / "raw/mac_trace/log.txt",
                        ],
                        repo,
                        self.output / "raw/mac_sql.log",
                    )
                else:
                    self.dail()
        for method in self.args.methods:
            self.command(
                [
                    sys.executable,
                    ROOT / f"scripts/normalize_{method}.py",
                    "--raw",
                    self.raw(method),
                    "--examples",
                    self.data / "examples.json",
                    "--output",
                    self.output / f"predictions/{method}.jsonl",
                ]
            )
        args = [
            sys.executable,
            ROOT / "scripts/evaluate.py",
            "--examples",
            self.data / "examples.json",
            "--subset",
            self.data / "subset.json",
            "--db",
            self.source / "database",
            "--table",
            self.data / "tables.json",
            "--summary",
            self.output / "summary.csv",
            "--work-dir",
            self.output / "evaluation",
            "--timeout",
            "1800",
        ]
        for method in self.args.methods:
            args += [
                "--prediction",
                f"{method}={self.output}/predictions/{method}.jsonl",
            ]
        self.command(args)


def main():
    cli = parser()
    try:
        Comparison(cli.parse_args()).run()
    except (ValueError, FileExistsError, FileNotFoundError, RuntimeError) as error:
        cli.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
