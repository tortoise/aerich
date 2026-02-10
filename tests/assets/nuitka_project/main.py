from app.database import bootstrap


def main() -> int:
    count, last = bootstrap()
    print(f"OK widgets={count} last={last}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
