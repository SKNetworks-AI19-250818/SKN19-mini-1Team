import argparse
import sys
import os

from preprocessing.preprocessing import save_all_preprocessed_data
from preprocessing.merge_datasets import save_final_dataset


def main():
    """
    Command-line interface for running data preprocessing and merging tasks.
    """
    parser = argparse.ArgumentParser(
        description="Run data preprocessing or merging for the SKN19-mini-1Team project."
    )
    subparsers = parser.add_subparsers(dest="task", required=True)

    # Preprocess command
    p_preprocess = subparsers.add_parser("preprocess", help="Run preprocessing for a specific year and mode.")
    p_preprocess.add_argument("--year", choices=["2022", "2023"], required=True, help="Year of the dataset to preprocess.")
    p_preprocess.add_argument("--mode", choices=["train", "validation"], required=True, dest="mode", help="Dataset mode (train or validation).")

    # Merge command
    p_merge = subparsers.add_parser("merge", help="Merge preprocessed data from all years for a specific mode.")
    p_merge.add_argument("--mode", choices=["train", "validation"], required=True, dest="mode", help="Dataset mode to merge (train or validation).")

    args = parser.parse_args()

    # Map CLI mode argument to directory names
    mode_to_dir = {
        "train": "training",
        "validation": "validation"
    }
    mode_dir_name = mode_to_dir[args.mode]

    if args.task == "preprocess":
        year = args.year
        
        preprocess_output_dir = os.path.join("data", mode_dir_name, year, "preprocessing")
        os.makedirs(preprocess_output_dir, exist_ok=True)
        
        print(f"Starting data preprocessing for '{year} {args.mode}' dataset...")
        try:
            saved_paths = save_all_preprocessed_data(output_dir=preprocess_output_dir, mode=mode_dir_name, year=year)
            print("Preprocessing finished successfully. Output files:")
            for key, path in saved_paths.items():
                print(f"  - {key}: {path}")
        except Exception as e:
            print(f"An error occurred during preprocessing: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.task == "merge":
        final_output_dir = os.path.join("data", mode_dir_name, "final")
        os.makedirs(final_output_dir, exist_ok=True)
        
        print(f"Starting dataset merging for all years for '{args.mode}' dataset...")
        try:
            final_path = save_final_dataset(mode=mode_dir_name, output_dir=final_output_dir)
            print(f"Merging finished successfully. Final dataset saved to:")
            print(f"  - {final_path}")
        except Exception as e:
            print(f"An error occurred during merging: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()