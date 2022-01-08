import { makeSignaller, RT, d3, globals} from "./cct_globals";
import { hierarchy as d3v7_hierarchy } from 'd3-hierarchy';

var createModel = function() {
    var _observers = makeSignaller();

    //initialize default data and state
    var _data = {
                    "trees":[],
                    "legends": ["Unified", "Indiv."],
                    "colors": ["Default", "Inverted"],
                    "forestData": null,
                    "rootNodeNames": ["Show all trees"],
                    "numberOfTrees": 0,
                    "metricColumns": [],
                    "attributeColumns": [],
                    "forestMinMax": [],
                    "aggregateMinMax": {},
                    "forestMetrics": [],
                    "metricLists":[],
                    "currentStrictness": 1.5,
                    "treeSizes": [],
                    "hierarchy": [],
                    "immutableHierarchy": [],
                    "maxHeight": 0
                };

    var _state = {
                    "selectedNodes":[], 
                    "collapsedNodes":[],
                    "primaryMetric": null,
                    "secondaryMetric": null,
                    "lastClicked": null,
                    "legend": 0,
                    "colorScheme": 0,
                    "brushOn": -1,
                    "hierarchyUpdated": true,
                    "cachedThreshold": 0,
                    "outlierThreshold": 0,
                    "pruneEnabled": false
                };

    //setup model
    let cleanTree = RT["hatchet_tree_def"];
    let _forestData = JSON.parse(cleanTree);
    _data.numberOfTrees = _forestData.length;
    _data.metricColumns = d3.keys(_forestData[0].metrics);
    _data["attributeColumns"] = d3.keys(_forestData[0].attributes);
    
    for(var metric = 0; metric < _data.metricColumns.length; metric++){
        let metricName = _data.metricColumns[metric];
        //remove private metric
        if(_data.metricColumns[metric][0] == '_'){
            _data.metricColumns.splice(metric, 1);
        }
        else{
            //setup aggregrate min max for metric
            _data.aggregateMinMax[metricName] = {min: Number.MAX_VALUE, max: Number.MIN_VALUE};
        }
    }

    // pick the first metric listed to color the nodes
    _state.primaryMetric = _data.metricColumns[0];
    _state.secondaryMetric = _data.metricColumns[1];
    _state.activeTree = "Show all trees";
    _state.treeXOffsets = [];
    
    let offset = 0;
    for (let treeIndex = 0; treeIndex < _forestData.length; treeIndex++) {
        let hierarchy = d3v7_hierarchy(_forestData[treeIndex], d => d.children);
        hierarchy.size = hierarchy.descendants().length;

        //add a surrogate id if _hatchet_nid is not present
        if(!Object.keys(hierarchy.descendants()[0].data.metrics).includes("_hatchet_nid")){
            hierarchy.descendants().forEach(function(d, i){
                d.data.metrics.id = offset+i;
            })
            offset += hierarchy.size;
        }

        _data.immutableHierarchy.push(hierarchy);
        _data.hierarchy.push(hierarchy);

        if (_data.immutableHierarchy[treeIndex].height > _data.maxHeight){
            _data.maxHeight = _data.immutableHierarchy[treeIndex].height;
        }
    }

    //sort in descending order
    _data.immutableHierarchy.sort((a,b) => b.size - a.size);
    _data.hierarchy.sort((a,b) => b.size - a.size);

    _state.lastClicked = _data.hierarchy[0];


    //Stats functions
    function _getListOfMetrics(h){
        //Gets a list of metrics with 0s removed
        // 0s in hpctoolkit are too numerous and they
        // throw off outlier calculations
        var list = [];
        
        h.each(d=>{
            if(d.data.metrics[_state.primaryMetric] != 0){
                list.push(d.data.metrics)
            }
        })

        return list;
    }

    function _asc(arr){
        /**
         *  Sorts an array in ascending order.
         */
        
        return arr.sort((a,b) => a[_state.primaryMetric]-b[_state.primaryMetric])
    }
    
    function _quantile(arr, q){
        /**
         * Gets a particular quantile from an array of numbers
         * 
         * @param {Array} arr - An array of floats
         * @param {Number} q - An float between [0-1] represening the quantile we want 
         */
        const sorted = _asc(arr);
        const pos = (sorted.length - 1) * q;
        const base = Math.floor(pos);
        const rest = pos - base;
        if (sorted[base + 1] !== undefined) {
            return sorted[base][_state.primaryMetric] + rest * (sorted[base + 1][_state.primaryMetric] - sorted[base][_state.primaryMetric]);
        } else {
            return sorted[base][_state.primaryMetric];
        }
    }

    function _getIQR(arr){
        /**
         * Returns the interquartile range for a an array of numbers
         */
        if(arr.length != 0){
            var q25 = _quantile(arr, .25);
            var q75 = _quantile(arr, .75);
            var IQR = q75 - q25;
            
            return IQR;
        }
        
        return NaN;
    }

    function _setOutlierFlags(h){
        /**
         * Sets outlier flags on a d3 hierarchy of call sites.
         * An outlier is defined as outside of the range between
         * the IQR*(a user defined scalar) + 75th quantile and
         * 25th quantile - IQR*(scalar). 
         * 
         * @param {Hierarchy} h - A d3 hierarchy containg metric values
         */
        var outlierScalar = _data.currentStrictness;
        var upperOutlierThreshold = Number.MAX_VALUE;
        var lowerOutlierThreshold = Number.MIN_VALUE;

        var metrics = _getListOfMetrics(h);

        var IQR = _getIQR(metrics);

        if(!isNaN(IQR)){
            upperOutlierThreshold = _quantile(metrics, .75) + (IQR * outlierScalar);
            lowerOutlierThreshold = _quantile(metrics, .25) - (IQR * outlierScalar);
        } 

        h.each(function(node){
            var metric = node.data.metrics[_state.primaryMetric];
            if(metric != 0 &&   //zeros are not interesting outliers
                metric >= upperOutlierThreshold || 
                metric <= lowerOutlierThreshold){
                node.data.outlier = 1;
            }
            else{
                node.data.outlier = 0;
            }
        })
    }


    function _getAggregateMetrics(h){
        /**
         * Utility function which gets aggregrate metrics for
         * a subtree.
         * 
         * @param {Hierarchy} h - A d3 hierarchy containing metrics
         */
        let agg = {};
        
        for(metric of _data.metricColumns){
            if(!metric.includes("(inc)")){
                h.sum(d=>{
                    if(d.aggregateMetrics){
                        return d.aggregateMetrics[metric];
                    } else{
                        return d.metrics[metric];
                    }
                });
                agg[metric] = h.value;
            }
            else{
                agg[metric] = h.data.metrics[metric];
            }
        }

        return agg;
    }

    function _getSubTreeDescription(h){
        /**
         * A utility function which returns a description of a subtree in terms
         * height, and number of nodes.
         * **TODO** - Add other descriptive details
         *
         * @param {Hierarchy} h - A d3 hierarchy containing metrics
         */
        let desc = {};
        console.log("HIERARCHY:", h);

        desc.height = h.height;
        desc.size = h.count().value;
        
        return desc;
    }

    function _buildDummyHolder(protoype, parent, elided){
        /**
         * A function that builds a surrogate node from a
         * prototype node and the parent associated with that
         * prototype.
         * 
         * @param {Node} prototype - A node which are going to replace with the resulting surrogate node
         *      A prototype is used here to preserve the descriptive stats of the removed node
         * @param {Node} parent - A node we are linking the new surrogate node to
         * @param {Node} elided - A list of sibling nodes which this surrogate is eliding from view
         */
        var dummyHolder = null;
        var aggregateMetrics = {};
        var description = {
            maxHeight: 0,
            minHeight: Number.MAX_VALUE,
            size: 0,
            elidedSubtrees:0
        };


        dummyHolder = protoype.copy();
        dummyHolder.depth = protoype.depth;
        dummyHolder.height = protoype.height;
        dummyHolder.children = null;

        //need a better way to make elided happen
        // pass in as arg makes sense
        dummyHolder.elided = elided;
        dummyHolder.dummy = true;
        dummyHolder.aggregate = false;
        dummyHolder.parent = parent;
        dummyHolder.outlier = 0;
        

        //initialize the aggregrate metrics for summing
        for(metric of _data.metricColumns){
            aggregateMetrics[metric] = 0;
        }

        for(elided of dummyHolder.elided){
            var aggMetsForChild = _getAggregateMetrics(elided);
            var descriptionOfChild = _getSubTreeDescription(elided);
            
            for(metric of _data.metricColumns){
                aggregateMetrics[metric] += aggMetsForChild[metric];
            }

            description.size += descriptionOfChild.size;

            if(descriptionOfChild.height > description.maxHeight){
                description.maxHeight = descriptionOfChild.height;
            }

            if(descriptionOfChild.height < description.minHeight){
                description.minHeight = descriptionOfChild.height;
            }

        }

        description.elidedSubtrees = elided.length;

        //get the overall min and max of aggregate metrics
        // for scales
        for(metric of _data.metricColumns){
            if (aggregateMetrics[metric] > _data.aggregateMinMax[metric].max){
                _data.aggregateMinMax[metric].max = aggregateMetrics[metric];
            }
            if(aggregateMetrics[metric] < _data.aggregateMinMax[metric].min){
                _data.aggregateMinMax[metric].min = aggregateMetrics[metric];
            }
        }

        dummyHolder.data.aggregateMetrics = aggregateMetrics;
        dummyHolder.data.description = description;

        //more than sum 0 nodes were aggregrated
        // together
        if(dummyHolder.data.aggregateMetrics[_state.primaryMetric] != 0){
            dummyHolder.aggregate = true;
        }

        return dummyHolder;
    }

    function _pruningVisitor(root, condition){
        /**
         * A recursive function that scans nodes for
         *  the existance of an outlier flag and manages the
         *  removal of non-outlier nodes in addition to the 
         *  creation of surrogate nodes that hold aggregated
         *  data.
         * 
         *  Note - The processing is done on the children of root primarily.
         *  
         *  @param {Hierarchy} root - Or current root node in our recursive scanning and modification of trees.
         *  @param {Number} condition - The comparision condition which our node value is compared against
         */
        if(root.children){
            var dummyHolder = null;
            var elided = [];
            
            for(var childNdx = root.children.length-1; childNdx >= 0; childNdx--){
                let child = root.children[childNdx];
                //clear dummy node codition so it
                // doesnt carry on between re-draws
                child.data.dummy = false;

                //condition where we remove child
                if(child.value < condition){
                    if(!root._children){
                        root._children = [];
                    }

                    elided.push(child);
                    root._children.push(child);
                    root.children.splice(childNdx, 1);
                }
            } 
            
            
            if (root._children && root._children.length > 0){
                dummyHolder = _buildDummyHolder(elided[0], root, elided);
                root.children.push(dummyHolder);
            }

            for(let child of root.children){
                _pruningVisitor(child, condition);
            }

            if(root.children.length == 0){
                root.children = null;
            }
        }
    }

    function _aggregateTreeData(){
        /**
         * Helper function which drives the outlier
         * detection and pruning of a fresh tree.
         * This function creates a fresh hierarchy when called and
         * overwrites the current tree in the view.
         */
        for(var i = 0; i < _data.numberOfTrees; i++){
            var h = _data.immutableHierarchy[i].copy();
            if(_data.currentStrictness > -1){
                //The sum ensures that we do not prune 
                //away parent nodes of identified outliers.
                _setOutlierFlags(h);
                h.sum(d => d.outlier);
                _pruningVisitor(h, 1);

                //update size of subtrees on the nodes
                h.size = h.descendants().length;
                
            }

            _data.hierarchy[i] = h;
        }
    }

    // --------------------------------------------
    // Node selection helper functions
    // --------------------------------------------

    function _printNodeData(nodeList) {
        /**
             * To pretty print the node data as a IPython table
             * 
             * @param {Array} nodeList - An array of selected nodes for formatting
             */
        
        var nodeStr = '<table><tr><td>name</td>';
        var numNodes = nodeList.length;
        var metricColumns = _data["metricColumns"];

        //lay the nodes out in a table
        for (let i = 0; i < metricColumns.length; i++) {
            nodeStr += '<td>' + metricColumns[i] + '</td>';
        }
        nodeStr += '</tr>';
        for (let i = 0; i < numNodes; i++) {
            nodeStr += "<tr>"
            for (var j = 0; j < metricColumns.length; j++) {
                if (j == 0) {
                    if (nodeList[i].data.aggregateMetrics && nodeList[i].elided.length == 1){
                        nodeStr += `<td>${nodeList[i].data.frame.name} Subtree </td>`
                    }
                    else if(nodeList[i].data.aggregateMetrics && nodeList[i].elided.length > 1){
                        nodeStr += `<td>Children of: ${nodeList[i].parent.data.frame.name} </td>`
                    }
                    else{
                        nodeStr += `<td>${nodeList[i].data.frame.name}</td>`;
                    }
                }
                if (nodeList[i].data.aggregateMetrics){
                    nodeStr += `<td>${nodeList[i].data.aggregateMetrics[metricColumns[j]]}</td>`
                }
                else{
                    nodeStr += `<td>${nodeList[i].data.metrics[metricColumns[j]]}</td>`
                }
            }
            nodeStr += '</tr>'
        }
        nodeStr = nodeStr + '</table>';

        return nodeStr;
    }

    function _printQuery(nodeList) {
        /**
             * Prints out user selected nodes as a query string which can be used in the GraphFrame.filter() function.
             * 
             * @param {Array} nodeList - An array of selected nodes for formatting
             */
        var leftMostNode = {depth: Number.MAX_VALUE, data: {name: 'default'}};
        var rightMostNode = {depth: 0, data: {name: 'default'}};
        var selectionIsAChain = false;

        for (var i = 0; i < nodeList.length; i++) {
            if (nodeList[i].depth < leftMostNode.depth) {
                leftMostNode = nodeList[i];
            }
            if (nodeList[i].depth > rightMostNode.depth) {
                rightMostNode = nodeList[i];
            }
            if ((i > 1) && (nodeList[i].x == nodeList[i-1].x)) {
                selectionIsAChain = true;
            }
            else {
                selectionIsAChain = false;
            }
        }

        //do some evaluation for other subtrees
        // we could generate python code that does this
        var queryStr = ['<no query generated>'];
        if ((nodeList.length > 1) && (selectionIsAChain)) {
            // This query is for chains
            queryStr = [{name: leftMostNode.data.frame.name }, '*', {name: rightMostNode.data.frame.name }];
        }
        else if (nodeList.length > 1) {
            // This query is for subtrees
            queryStr = [{name: leftMostNode.data.frame.name }, '*', {depth: '<=' + rightMostNode.depth}];
        }
        else {
            //Single node query
            queryStr = [{name: leftMostNode.data.frame.name}];
        }

        return queryStr;
    }


    //-------------------------------------------
    // Model Setup Processing
    //-------------------------------------------


    //get the max and min metrics across the forest
    // and for each individual tree
    var _forestMetrics = [];
    var _forestMinMax = {}; 

    for (var index = 0; index < _data.numberOfTrees; index++) {
        var thisTree = _forestData[index];
        let mc = _data.metricColumns;

        // Get tree names for the display select options
        _data["rootNodeNames"].push(thisTree.frame.name);

        var thisTreeMetrics = {};

        for (var j = 0; j < mc.length; j++) {
            thisTreeMetrics[mc[j]] = {};
            thisTreeMetrics[mc[j]]["min"] = Number.MAX_VALUE;
            thisTreeMetrics[mc[j]]["max"] = 0;

            //only one run time
            if(index == 0){
                _forestMinMax[mc[j]] = {};
                _forestMinMax[mc[j]]["min"] = Number.MAX_VALUE;
                _forestMinMax[mc[j]]["max"] = 0;
            }
        }

        _data['hierarchy'][index].each(function (d) {
            for (var i = 0; i < mc.length; i++) {
                var tempMetric = mc[i];
                if (d.data.metrics[tempMetric] > thisTreeMetrics[tempMetric].max) {
                    thisTreeMetrics[tempMetric].max = d.data.metrics[tempMetric];
                }
                if (d.data.metrics[tempMetric] < thisTreeMetrics[tempMetric].min) {
                    thisTreeMetrics[tempMetric].min = d.data.metrics[tempMetric];
                }
                if (d.data.metrics[tempMetric] > _forestMinMax[tempMetric].max) {
                    _forestMinMax[tempMetric].max = d.data.metrics[tempMetric];
                }
                if (d.data.metrics[tempMetric] < _forestMinMax[tempMetric].min) {
                    _forestMinMax[tempMetric].min = d.data.metrics[tempMetric];
                }
            }
        });

        _forestMetrics.push(thisTreeMetrics);
    }
    _data.forestMetrics = _forestMetrics;

    // Global min/max are the last entry of forestMetrics;
    _data.forestMinMax = _forestMinMax;
    _data.forestMetrics.push(_forestMinMax);

    return{
        data: _data,
        state: _state,
        register: function(s){
            /**
             * Registers a signaller (a callback function) to be run with _observers.notify()
             * 
             * @param {Function} s - (a callback function) to be run with _observers.notify()
             */
            _observers.add(s);
        },
        enablePruneTree: function(enabled, threshold){
            /**
             * Enables/disables the mass prune tree functionality.
             * Prunes tree on click based on current slider position.
             * 1.5 by default from view.
             * 
             * @param {bool} enabled - Switch bool that guides if we disable or enable mass pruning
             * @param {float} threshold - User defined strictness of pruning. Used as the multiplier in set outlier flags.
             *      On first click this will be 1.5.
             */
            if (enabled){
                _state.pruneEnabled = true;
                _data.currentStrictness = threshold;
                _aggregateTreeData();
                _state.hierarchyUpdated = true;
            } 
            else{
                _state.pruneEnabled = false;
                // threshold = -1;
            }
            
            _observers.notify();
            
        },
        pruneTree: function(threshold){
            /**
             * Interface to the private tree aggregation functions.
             *  Calls when user adjusts automatic pruning slider.
             * 
             * @param {float} threshold - User defined strictness of pruning. Used as the multiplier in set outlier flags.
             */
            _data.currentStrictness = threshold;
            _aggregateTreeData();
            _state.hierarchyUpdated = true;

            _observers.notify();
        },
        updateSelected: function(nodes){
            /**
             * Updates which nodes are "Selected" by the user in the model
             *
             * @param {Array} nodes - A list of selected nodes
             */
            _state['selectedNodes'] = nodes;
            this.updateTooltip(nodes);

            if(nodes.length > 0 && nodes[0]){
                RT['jsNodeSelected'] = JSON.stringify(_printQuery(nodes));
            } else {
                RT['jsNodeSelected'] = JSON.stringify(["*"]);
            }
            
            _observers.notify();
        },
        handleDoubleClick: function(d){
            /**
             * Manages the collapsing and expanding of subtrees
             *  when a user is manually pruning or exploring a tree.
             * 
             * @param {node} d - The node the user just double clicked.
             *      Can be a surrogate or real node.
             */
            //hiding a subtree
            if(!d.dummy){
                if(d.parent){
                    //main manipulation is in parent scope
                    let children = d.parent.children;

                    if(!d.parent._children){
                        d.parent._children = [];
                    }

                    d.parent._children.push(d);
                    let dummy = _buildDummyHolder(d, d.parent, [d]);
                    let swapIndex = d.parent.children.indexOf(d);
                    children[swapIndex] = dummy;
                }
            } 

            // Expanding a dummy node 
            // Replaces a node if one was elided
            // Appends if multiple were elided
            else{
                
                if(d.elided.length == 1){
                    // patch that clears aggregate metrics upon doubleclick
                    delete d.elided[0].data.aggregateMetrics;

                    let insIndex = d.parent.children.indexOf(d);
                    d.parent.children[insIndex] = d.elided[0];
                }
                else{
                    for(let elided of d.elided){
                        delete elided.data.aggregateMetrics;
                        let delIndex = d.parent._children.indexOf(elided);
                        d.parent._children.splice(delIndex, 1);

                        d.parent.children.push(elided);
                    }
                    d.parent.children = d.parent.children.filter(child => child !== d);
                }
            }

            _state["lastClicked"] = d;

            _state.hierarchyUpdated = true;
            _observers.notify();
        },
        toggleBrush: function(){
            /**
             * Toggles the brushing functionality with a button click
             *
             */

            _state["brushOn"] = -_state["brushOn"];
            _observers.notify();
        },
        setBrushedPoints: function(selection){
            /**
             * Calculates which nodes are in the brushing area.
             * 
             * @param {Array} selection - Selected nodes
             *
             */

            console.log(selection);
            if(selection){
                this.updateSelected(selection);
            }
            else{
                this.updateSelected([]);
            }
            
        },
        updateTooltip: function(nodes){
            /**
             * Updates the model with new tooltip information based on user selection
             * 
             * @param {Array} nodes - A list of selected nodes
             *
             */
            if(nodes.length > 0 && nodes[0]){
                var longestName = 0;
                nodes.forEach(function (d) {
                    var nodeData = d.data.frame.name + ': ' + d.data.metrics.time + 's (' + d.data.metrics["time (inc)"] + 's inc)';
                    if (nodeData.length > longestName) {
                        longestName = nodeData.length;
                    }
                });
                _data["tipText"] = _printNodeData(nodes);
            } 
            else{
                _data["tipText"] = '<p>Click a node or "Select nodes" to see more info</p>';
            }
        },
        changeMetric: function(newMetric, source){
                /**
             * Changes the currently selected metric in the model.
             * 
             * @param {String} newMetric - the most recently selected metric
             *
             */

            if(source.includes("primary")){
                _state.primaryMetric = newMetric;
            } 
            else if(source.includes("secondary")){
                _state.secondaryMetric = newMetric;
            }
            
            if(_state.pruneEnabled){
                _aggregateTreeData();
                _state.hierarchyUpdated = true;
            }
            _observers.notify();
        },
        changeColorScheme: function(){
            /**
             * Changes the current color scheme to inverse or regular. Updates the view
             *
             */

            //loop through the possible color schemes
            _state["colorScheme"] = (_state["colorScheme"] + 1) % _data["colors"].length;
            _observers.notify();
        },
        updateLegends: function(){
            /**
             * Toggles between divergent or unified legends. Updates the view
             *
             */
            //loop through legend configruations
            _state["legend"] = (_state["legend"] + 1) % _data["legends"].length;
            _observers.notify();
        },
        updateActiveTrees: function(activeTree){
            /**
             * Sets which tree is currently "active" in the model. Updates the view.
             *
             */
            _state["activeTree"] = activeTree;
            _observers.notify();
        },
        resetView(){
            /**
             * Function that sets a flag which causes the 
             * view to reset all trees to their original layouts.
             */
            _state.resetView = true;
            _observers.notify();
        }
    }
}

export default createModel;