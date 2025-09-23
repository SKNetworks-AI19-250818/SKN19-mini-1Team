import argparse
import sys

from preprocessing.preprocessing import save_all_preprocessed_data
from preprocessing.merge_datasets import save_final_dataset


def main():
    """
    Command-line interface for running data preprocessing and merging tasks.
    """
    parser = argparse.ArgumentParser(
        description="Run data preprocessing or merging for the SKN19-mini-1Team project."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--preprocess",
        action="store_true",
        help="Run all preprocessing steps from preprocessing.py and save the results.",
    )
    group.add_argument(
        "--merge",
        action="store_true",
        help="Merge preprocessed datasets into a final dataset using merge_datasets.py.",
    )

    args = parser.parse_args()

    if args.preprocess:
        print("Starting data preprocessing...")
        try:
            saved_paths = save_all_preprocessed_data()
            print("Preprocessing finished successfully. Output files:")
            for key, path in saved_paths.items():
                print(f"  - {key}: {path}")
        except Exception as e:
            print(f"An error occurred during preprocessing: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.merge:
        print("Starting dataset merging...")
        try:
            final_path = save_final_dataset()
            print(f"Merging finished successfully. Final dataset saved to:")
            print(f"  - {final_path}")
        except Exception as e:
            print(f"An error occurred during merging: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
