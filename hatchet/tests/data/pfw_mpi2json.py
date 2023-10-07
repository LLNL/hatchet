import os
import subprocess
import json

# Directory path where your files are located
folder_path = 'ams_mpi_test1'

# Check if the folder exists
if not os.path.exists(folder_path):
    print("The specified folder does not exist.")
    exit()

# Initialize a file index
file_index = 0

# Loop through each file in the folder
for filename in os.listdir(folder_path):
    if filename.endswith(".pfw"):
        file_path = os.path.join(folder_path, filename)
        print(file_path) 
        # Check if it's a file (not a subdirectory)
        if os.path.isfile(file_path):
            # Call format.py with the file name and index as arguments
            subprocess.run(['python', 'pfw2json.py', str(file_index), file_path])
            
            # Increment the file index
            file_index += 1


'''
    the following code combines all .json files within the folder into the same file
'''
# Initialize a list to store the data from all files
all_data = []

# Loop through the files in the folder
for filename in os.listdir(folder_path):
    if filename.endswith('.json'):
        file_path = os.path.join(folder_path, filename)
        with open(file_path, 'r') as file:
            # Load the JSON data from the file
            data = json.load(file)
            
            # Append the data to the list
            all_data.extend(data['data'])

# sort data accordingly
def sort_data(item):
    return (item[2], item[1])

# Sort the data using the custom key function for each sublist
sorted_data = sorted(all_data, key=sort_data)

# Create the final result dictionary
final_result = {
    'data': sorted_data,
    'columns': data['columns'],  # Assuming columns are the same for all files
    'column_metadata': data['column_metadata'],  # Assuming column_metadata is the same for all files
    'nodes': data['nodes'],  # Assuming nodes are the same for all files
}

final_result_path = 'final_result.json'
with open(final_result_path, 'w') as final_file:
    json.dump(final_result, final_file, indent=2)
