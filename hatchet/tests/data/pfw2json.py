import json
import sys

if len(sys.argv) != 3:
    print("Usage: script.py <rank> <file_name>")
    sys.exit(1)

rank = sys.argv[1]
file_name = sys.argv[2]


# Read the JSON file
with open(file_name, 'r') as file:
    content = file.read()

# Load the JSON content
data = json.loads(content)

# Function to recursively compare tree structures and aggregate durations
def compare_and_aggregate(node1, node2):
    if node1['name'] != node2['name']:
        return False
    
    if len(node1['children']) != len(node2['children']):
        return False
    
    for child1, child2 in zip(node1['children'], node2['children']):
        if not compare_and_aggregate(nodes[child1], nodes[child2]):
            return False
   
    node1['dur'] += node2['dur']
    return True

# Data structure to store index, name, duration, and children
nodes = {}
roots = []

# Process each item in the data
for index, item in enumerate(data):
    name = item['name']
    dur = item['dur']
    ts = item['ts']

    parent_found = False

    # Check the relationships between node and roots
    for idx, root in enumerate(reversed(roots)):
        # if node is a parent of root node
        if (ts < root['ts']) and (ts + dur > root['ts'] + root['dur']):
            level_start = len(roots) - idx - 1
            parent_found = True
        else:
            break    
    
    if not parent_found:
        nodes[index] = {'name': name, 'dur': dur, 'children': []}
    else:
        # aggregate at current level
        i = level_start 
        while i < len(roots):
            j = i 
            while j < len(roots):
                root1 = roots[i]
                root2 = roots[j]
                if i != j:
                    if compare_and_aggregate(nodes[root1['index']], nodes[root2['index']]):
                        roots.pop(j)
                        nodes.pop(root2['index'])
                    else:
                        j += 1    
                else:
                    j += 1
            i += 1
        # if parent found, add aggregated children
        for root in roots[level_start:]:
            if index not in nodes:
                nodes[index] = {'name': name, 'dur': dur, 'children': []}
            if root['index'] not in nodes[index]['children']:
                nodes[index]['children'].append(root['index'])
                roots.pop()
    roots.append({'index': index, 'name': name, 'ts': ts, 'dur': dur})

# aggregate at current level
i = 0 
while i < len(roots):
    j = i 
    while j < len(roots):
        root1 = roots[i]
        root2 = roots[j]
        if i != j:
            if compare_and_aggregate(nodes[root1['index']], nodes[root2['index']]):
                roots.pop(j)
                nodes.pop(root2['index'])
            else:
                j += 1    
        else:
            j += 1
    i += 1

# Function to recursively generate the JSON data for a node
def generate_json_data(node_index, parent_index=None, index_counter=[0]):
    node = nodes[node_index]
    children = []

    json_node = [node['dur'], int(rank), index_counter[0]]
    index_counter[0] += 1

    json_data.append(json_node)
    
    if 'children' in node and node['children']:
        for child_name in node.get('children', []):
            child = nodes[child_name]
            children.append(generate_json_data(child_name, node_index, index_counter))

def generate_json_nodes(node_index, offset, index_counter = None, parent_index=None):
    if index_counter is None:
       index_counter = [0]

    node = nodes[node_index]
    children = []

    if parent_index is None:
        node_info = [{"column": "path", "label": node['name']}]  
    else:
        # print("parent: ", parent_index, "offset: ", offset)
        node_info = [{"column": "path", "label": node['name'], "parent": parent_index+offset}]
    parent_index = index_counter[0]
    index_counter[0] += 1
    if 'children' in node and node['children']:
        for child_index in node.get('children', []):
            child = nodes[child_index]
            node_info.extend(generate_json_nodes(child_index, offset, index_counter, parent_index))

    return node_info

# Loop through each root node and generate the JSON data and nodes
json_data = []
for root in roots:
    generate_json_data(root['index'])

json_nodes = []
for root in roots:
    offset = len(json_nodes)
    json_nodes.extend(generate_json_nodes(root['index'], offset))

# Define the JSON structure
json_structure = {
    "data": json_data,
    "columns": ["dur", "rank", "path"],
    "column_metadata": [{"is_value": True}, {"is_value": True}, {"is_value": False}],
    "nodes":json_nodes
}

output_name = file_name[0:-4] + ".json"
with open(output_name, 'w') as file:
    json.dump(json_structure, file, indent=1, separators=(',', ': '))

