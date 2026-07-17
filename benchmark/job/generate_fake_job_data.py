#!/usr/bin/env python3
"""Generate fake job dataset CSVs under benchmark/job/data2/."""
from __future__ import annotations

import csv
import hashlib
import random
from pathlib import Path
from typing import Any

from faker import Faker

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "data2"

fake = Faker()
random.seed(42)
Faker.seed(42)

NUM_NAMES = 500
NUM_TITLES = 300
NUM_KEYWORDS = 200
NUM_COMPANIES = 100
NUM_AKA_NAME = 300
NUM_AKA_TITLE = 300
NUM_CAST_INFO = 1000
NUM_CHAR_NAME = 200
NUM_COMPLETE_CAST = 400
NUM_MOVIE_COMPANIES = 400
NUM_MOVIE_INFO_IDX = 800
NUM_MOVIE_KEYWORD = 800
NUM_MOVIE_LINK = 400
NUM_MOVIE_INFO = 800
NUM_PERSON_INFO = 500

COMP_CAST_TYPES = [
    "producer",
    "director",
    "editor",
    "cinematographer",
    "costume designer",
    "composer",
    "stunt coordinator",
    "visual effects",
    "sound mixer",
    "makeup artist",
]
COMPANY_TYPES = [
    "production company",
    "distributor",
    "special effects",
    "marketing",
    "studio",
    "finance",
    "post-production",
    "animation",
    "music publisher",
    "talent agency",
]
INFO_TYPES = [
    "plot",
    "runtime",
    "awards",
    "genre",
    "release date",
    "language",
    "country",
    "budget",
    "box office",
    "tagline",
    "trivia",
    "soundtrack",
    "certification",
    "original language",
    "filming locations",
    "distributor",
    "production status",
    "filming dates",
    "technical specs",
    "alternate titles",
]
KIND_TYPES = [
    "movie",
    "tv series",
    "tv movie",
    "video",
    "tv episode",
    "documentary",
    "short",
    "music video",
    "game",
    "soundtrack",
]
LINK_TYPES = [
    "sequel",
    "prequel",
    "remake",
    "spin-off",
    "alternate version",
    "same universe",
    "companion",
    "narrative",
    "remaster",
    "adaptation",
]
ROLE_TYPES = [
    "actor",
    "actress",
    "director",
    "writer",
    "producer",
    "cinematographer",
    "editor",
    "composer",
    "sound designer",
    "stunt performer",
]
COUNTRY_CODES = ["US", "GB", "CA", "FR", "DE", "JP", "IN", "IT", "AU", "BR"]


def md5sum(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def write_csv(path: Path, rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(rows)


def random_code(length: int) -> str:
    return fake.bothify("?" * length).upper()


def generate_lookup_table(values: list[str]) -> list[list[Any]]:
    return [[idx + 1, value] for idx, value in enumerate(values)]


def generate_keyword_rows(count: int) -> list[list[Any]]:
    return [
        [
            idx + 1,
            fake.word().replace("_", " ").title(),
            random_code(5),
        ]
        for idx in range(count)
    ]


def generate_name_rows(count: int) -> list[list[Any]]:
    rows = []
    for idx in range(count):
        person_name = fake.name()
        rows.append(
            [
                idx + 1,
                person_name,
                fake.bothify("??###"),
                fake.random_int(min=1000, max=9999),
                fake.random_element(["m", "f"]),
                random_code(5),
                random_code(5),
                random_code(5),
                md5sum(person_name),
            ]
        )
    return rows


def generate_title_rows(count: int, kind_count: int) -> list[list[Any]]:
    rows = []
    for idx in range(count):
        title_text = fake.sentence(nb_words=4).rstrip(".")
        kind_id = random.randint(1, kind_count)
        production_year = fake.random_int(min=1960, max=2024)
        episode_of_id = None
        season_nr = None
        episode_nr = None
        series_years = ""
        if kind_id == 5 or random.random() < 0.10:
            episode_of_id = random.randint(1, count)
            season_nr = random.randint(1, 12)
            episode_nr = random.randint(1, 24)
            start_year = production_year - random.randint(0, 3)
            end_year = production_year
            series_years = f"{start_year}-{end_year}"

        rows.append(
            [
                idx + 1,
                title_text,
                fake.bothify("?????"),
                kind_id,
                production_year,
                fake.random_int(min=10000, max=99999),
                random_code(5),
                episode_of_id or "",
                season_nr or "",
                episode_nr or "",
                series_years,
                md5sum(title_text),
            ]
        )
    return rows


def generate_company_rows(count: int) -> list[list[Any]]:
    return [
        [
            idx + 1,
            fake.company(),
            fake.random_element(COUNTRY_CODES),
            fake.random_int(min=1000, max=9999),
            random_code(5),
            random_code(5),
            md5sum(fake.company()),
        ]
        for idx in range(count)
    ]


def generate_char_name_rows(count: int) -> list[list[Any]]:
    rows = []
    for idx in range(count):
        name_text = fake.first_name() + " " + fake.last_name()
        rows.append(
            [
                idx + 1,
                name_text,
                fake.bothify("??"),
                fake.random_int(min=1000, max=9999),
                random_code(5),
                random_code(5),
                md5sum(name_text),
            ]
        )
    return rows


def generate_aka_name_rows(count: int, name_count: int) -> list[list[Any]]:
    return [
        [
            idx + 1,
            random.randint(1, name_count),
            fake.name(),
            fake.bothify("???"),
            random_code(11),
            random_code(11),
            random_code(11),
            md5sum(fake.name()),
        ]
        for idx in range(count)
    ]


def generate_aka_title_rows(count: int, title_count: int, kind_count: int) -> list[list[Any]]:
    rows = []
    for idx in range(count):
        note = fake.sentence(nb_words=8)
        episode_of_id = ""
        season_nr = ""
        episode_nr = ""
        if random.random() < 0.10:
            episode_of_id = random.randint(1, title_count)
            season_nr = random.randint(1, 15)
            episode_nr = random.randint(1, 30)
        rows.append(
            [
                idx + 1,
                random.randint(1, title_count),
                fake.sentence(nb_words=3).rstrip("."),
                fake.bothify("????"),
                random.randint(1, kind_count),
                fake.random_int(min=1970, max=2024),
                random_code(5),
                episode_of_id,
                season_nr,
                episode_nr,
                note,
                md5sum(fake.sentence(nb_words=3)),
            ]
        )
    return rows


def generate_cast_info_rows(count: int, name_count: int, title_count: int, role_count: int) -> list[list[Any]]:
    return [
        [
            idx + 1,
            random.randint(1, name_count),
            random.randint(1, title_count),
            fake.random_int(min=1, max=10),
            fake.sentence(nb_words=6),
            random.randint(1, 30),
            random.randint(1, role_count),
        ]
        for idx in range(count)
    ]


def generate_complete_cast_rows(count: int, title_count: int) -> list[list[Any]]:
    return [
        [
            idx + 1,
            random.randint(1, title_count),
            random.randint(1, title_count),
            random.randint(1, 5),
        ]
        for idx in range(count)
    ]


def generate_movie_companies_rows(count: int, title_count: int, company_count: int, company_type_count: int) -> list[list[Any]]:
    return [
        [
            idx + 1,
            random.randint(1, title_count),
            random.randint(1, company_count),
            random.randint(1, company_type_count),
            fake.sentence(nb_words=8),
        ]
        for idx in range(count)
    ]


def generate_movie_info_idx_rows(count: int, title_count: int, info_type_count: int) -> list[list[Any]]:
    return [
        [
            idx + 1,
            random.randint(1, title_count),
            random.randint(1, info_type_count),
            fake.sentence(nb_words=10),
            random.choice(["", "A", "B", "C", "D"]),
        ]
        for idx in range(count)
    ]


def generate_movie_keyword_rows(count: int, title_count: int, keyword_count: int) -> list[list[Any]]:
    return [
        [
            idx + 1,
            random.randint(1, title_count),
            random.randint(1, keyword_count),
        ]
        for idx in range(count)
    ]


def generate_movie_link_rows(count: int, title_count: int, link_type_count: int) -> list[list[Any]]:
    return [
        [
            idx + 1,
            random.randint(1, title_count),
            random.randint(1, title_count),
            random.randint(1, link_type_count),
        ]
        for idx in range(count)
    ]


def generate_movie_info_rows(count: int, title_count: int, info_type_count: int) -> list[list[Any]]:
    return [
        [
            idx + 1,
            random.randint(1, title_count),
            random.randint(1, info_type_count),
            fake.sentence(nb_words=10),
            fake.sentence(nb_words=8),
        ]
        for idx in range(count)
    ]


def generate_person_info_rows(count: int, name_count: int, info_type_count: int) -> list[list[Any]]:
    return [
        [
            idx + 1,
            random.randint(1, name_count),
            random.randint(1, info_type_count),
            fake.sentence(nb_words=10),
            fake.sentence(nb_words=8),
        ]
        for idx in range(count)
    ]


def main() -> None:
    rows = {
        "comp_cast_type.csv": generate_lookup_table(COMP_CAST_TYPES),
        "company_type.csv": generate_lookup_table(COMPANY_TYPES),
        "info_type.csv": generate_lookup_table(INFO_TYPES),
        "kind_type.csv": generate_lookup_table(KIND_TYPES),
        "link_type.csv": generate_lookup_table(LINK_TYPES),
        "role_type.csv": generate_lookup_table(ROLE_TYPES),
        "keyword.csv": generate_keyword_rows(NUM_KEYWORDS),
        "name.csv": generate_name_rows(NUM_NAMES),
        "title.csv": generate_title_rows(NUM_TITLES, len(KIND_TYPES)),
        "company_name.csv": generate_company_rows(NUM_COMPANIES),
        "char_name.csv": generate_char_name_rows(NUM_CHAR_NAME),
        "aka_name.csv": generate_aka_name_rows(NUM_AKA_NAME, NUM_NAMES),
        "aka_title.csv": generate_aka_title_rows(NUM_AKA_TITLE, NUM_TITLES, len(KIND_TYPES)),
        "cast_info.csv": generate_cast_info_rows(NUM_CAST_INFO, NUM_NAMES, NUM_TITLES, len(ROLE_TYPES)),
        "complete_cast.csv": generate_complete_cast_rows(NUM_COMPLETE_CAST, NUM_TITLES),
        "movie_companies.csv": generate_movie_companies_rows(NUM_MOVIE_COMPANIES, NUM_TITLES, NUM_COMPANIES, len(COMPANY_TYPES)),
        "movie_info_idx.csv": generate_movie_info_idx_rows(NUM_MOVIE_INFO_IDX, NUM_TITLES, len(INFO_TYPES)),
        "movie_keyword.csv": generate_movie_keyword_rows(NUM_MOVIE_KEYWORD, NUM_TITLES, NUM_KEYWORDS),
        "movie_link.csv": generate_movie_link_rows(NUM_MOVIE_LINK, NUM_TITLES, len(LINK_TYPES)),
        "movie_info.csv": generate_movie_info_rows(NUM_MOVIE_INFO, NUM_TITLES, len(INFO_TYPES)),
        "person_info.csv": generate_person_info_rows(NUM_PERSON_INFO, NUM_NAMES, len(INFO_TYPES)),
    }

    for name, table_rows in rows.items():
        output_path = OUTPUT_DIR / name
        write_csv(output_path, table_rows)
        print(f"Generated {len(table_rows)} rows -> {output_path}")


if __name__ == "__main__":
    main()
