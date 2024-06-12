
import re # for manipulating strings
import pandas as pd

def sanitize_description(description):
    allowed_characters_pattern = r"[^a-zA-Z0-9.,:;_ \-]"  # Define a regex pattern for characters not in the allowed set
    sanitized_description = re.sub(allowed_characters_pattern, "", description)  # Remove characters not in the allowed set
    return sanitized_description


def append_excel_files(file_paths, num_sheets, output_file_path):
    # Initialize a dictionary to store combined DataFrames from different files
    combined_dfs = {}

    # Initialize a counter to track the progress of file processing
    counter = 0

    # Iterate over each file path in the list
    for file_path in file_paths:
        # Load the Excel file
        # xls = pd.ExcelFile(file_path)  # Reads file and stores as an ExcelFile object (using the Pandas library)
        xls = pd.ExcelFile(file_path, engine='openpyxl')  # Reads file and stores as an ExcelFile object (using the Pandas library)

        # xls = pd.ExcelFile(file_path, engine='xlrd')  # Reads file and stores as an ExcelFile object (using the Pandas library)

        # Increment the counter for each iteration
        counter += 1

        # Read each sheet from the Excel file into a DataFrame
        # Only read up to num_sheets specified
        dfs = {sheet_name: xls.parse(sheet_name) for sheet_name in xls.sheet_names[:num_sheets]}

        # Append the DataFrames to the combined_dfs dictionary
        for sheet_name, df in dfs.items():
            if sheet_name in combined_dfs:
                # If the sheet already exists in combined_dfs, concatenate the current DataFrame with the existing one
                combined_dfs[sheet_name] = pd.concat([combined_dfs[sheet_name], df], ignore_index=True)
            else:
                # If the sheet does not exist in combined_dfs, add the DataFrame directly
                combined_dfs[sheet_name] = df

        # Print the progress of processing, overwriting the previous progress
        print(f"\rProcessing {counter}/{len(file_paths)}: {file_path}", end="")

    # Write the combined DataFrames to the specified output file path
    with pd.ExcelWriter(output_file_path) as writer:
        for sheet_name, df in combined_dfs.items():
            # Write each DataFrame to a separate sheet in the output Excel file
            df.to_excel(writer, sheet_name=sheet_name, index=False)

