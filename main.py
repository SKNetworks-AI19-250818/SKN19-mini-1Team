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
    
    # Group to select the dataset mode (train or validate)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--train",
        action="store_true",
        help="Run tasks on the training dataset."
    )
    mode_group.add_argument(
        "--validate",
        action="store_true",
        help="Run tasks on the validation dataset."
    )

    # Group to select the task (preprocess or merge)
    task_group = parser.add_mutually_exclusive_group(required=True)
    task_group.add_argument(
        "--preprocess",
        action="store_true",
        help="Run all preprocessing steps and save the results.",
    )
    task_group.add_argument(
        "--merge",
        action="store_true",
        help="Merge preprocessed datasets into a final dataset.",
    )

    args = parser.parse_args()

    # Determine mode and paths
    if args.train:
        mode = "train"
        preprocess_output_dir = os.path.join("data", "training", "preprocessing")
        final_output_dir = os.path.join("data", "training", "final")
    else: # args.validate
        mode = "validation"
        preprocess_output_dir = os.path.join("data", "validation", "preprocessing")
        final_output_dir = os.path.join("data", "validation", "final")
        
    # Ensure the output directory for the final merged file exists
    os.makedirs(final_output_dir, exist_ok=True)


    if args.preprocess:
        print(f"Starting data preprocessing for '{mode}' dataset...")
        try:
            # Pass mode and the correct output directory
            saved_paths = save_all_preprocessed_data(output_dir=preprocess_output_dir, mode=mode)
            print("Preprocessing finished successfully. Output files:")
            for key, path in saved_paths.items():
                print(f"  - {key}: {path}")
        except Exception as e:
            print(f"An error occurred during preprocessing: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.merge:
        print(f"Starting dataset merging for '{mode}' dataset...")
        try:
            # Pass mode and the final output directory
            final_path = save_final_dataset(mode=mode, output_dir=final_output_dir)
            print(f"Merging finished successfully. Final dataset saved to:")
            print(f"  - {final_path}")
        except Exception as e:
            print(f"An error occurred during merging: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()