import json

# Read the JSON file
with open('perfflow.quartz1532.3570764.pfw', 'r') as file:
    content = file.read()

# Load the JSON content
data = json.loads(content)

# Data structure to store name and duration
nodes = {}

roots = []

# Process each item in the data
for item in data:
    name = item['name']
    dur = item['dur']
    ts = item['ts']

    # Check the relationships between node and roots
    for root in reversed(roots):
        # if node is a parent of root node
        if (ts < root['ts']) and (ts + dur > root['ts'] + root['dur']):
            if name not in nodes:
                nodes[name] = {'dur': 0, 'children':[]}
            if root['name'] not in nodes[name]['children']:
                nodes[name]['children'].append(root['name'])
            roots.pop()
    
    if name not in [root['name'] for root in roots]: 
        roots.append(item)  # Add current node to the list of roots

    # Check if the name is already in the data structure
    if name in nodes:
        nodes[name]['dur'] += dur
    else:
        nodes[name] = {'dur': dur}

# Print the nodes and their relationships
# for name, info in nodes.items():
#     children = info.get('children', [])
#     print(f"Name: {name}, Duration: {info['dur']}, Children: {children}")

# Function to recursively generate the formatted output
def format_node(node_name, depth=0):
    node = nodes[node_name]
    indent = "    " * depth
    children = []

    for child_name in node.get('children', []):
        child = nodes[child_name]
        children.append(format_node(child_name, depth + 1))

    frame_info = {
        "name": node_name,
        # Add other frame information here if available in your nodes
    }

    metrics_info = {
        "dur": node['dur'],
        # Add other metrics information here if available in your nodes
    }

    formatted_children = ",\n".join(children)

    return (
        f"{indent}{{\n"
        f"{indent}    \"frame\": {json.dumps(frame_info)},\n"
        f"{indent}    \"metrics\": {json.dumps(metrics_info)},\n"
        f"{indent}    \"children\": [\n{formatted_children}\n{indent}    ]\n"
        f"{indent}}}"
    )

# Loop through each root node and write its formatted information to a file
with open('formatted_literal', 'w') as file:
    file.write("[\n")
    for root in roots:
        formatted_output = format_node(root['name'])
        file.write(formatted_output)
        file.write('\n')  # Add a newline after each node
    file.write("]\n")
