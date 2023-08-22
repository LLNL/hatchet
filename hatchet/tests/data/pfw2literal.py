import json

# Read the JSON file
# with open('perfflow.quartz1532.3570764.pfw', 'r') as file:
with open('laghos_1iter.pfw', 'r') as file:
# with open('ams_test1.pfw', 'r') as file:
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


# print("nodes: ", nodes)
# print("roots: ", roots)


# Function to recursively generate the formatted output
def format_node(node_name, depth=0):
    node = nodes[node_name]
    indent = "    " * depth
    children = []

    if 'children' in node and node['children']:
        for child_name in node.get('children', []):
            child = nodes[child_name]
            children.append(format_node(child_name, depth + 1))

    frame_info = {
        # "name": node_name,
        "name": node['name']    
        # Add other frame information here if available in your nodes
    }

    metrics_info = {
        "dur": node['dur'],
        # Add other metrics information here if available in your nodes
    }

    formatted_children = ",\n".join(children)
    children_output = f",\n{indent}    \"children\": [\n{formatted_children}\n{indent}    ]" if formatted_children else ""
    
    return (
        f"{indent}{{\n"
        f"{indent}    \"frame\": {json.dumps(frame_info)},\n"
        f"{indent}    \"metrics\": {json.dumps(metrics_info)}{children_output}\n"
        f"{indent}}}"
    )

# Loop through each root node and write its formatted information to a file
with open('formatted_literal', 'w') as file:
    file.write("[\n")
    num_roots = len(roots)
    
    for index, root in enumerate(roots):
        formatted_output = format_node(root['index'])
        file.write(formatted_output)
        
        if index < num_roots - 1:
            file.write(',')  # Add a comma after each node except the last one
        
        file.write('\n')  # Add a newline after each node
    '''
    for root in unique_roots:
        formatted_output = format_node(root['name'])
        file.write(formatted_output)
        file.write('\n')  # Add a newline after each node
    '''
    file.write("]\n")
    
