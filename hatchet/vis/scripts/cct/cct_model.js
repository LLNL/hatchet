import { makeSignaller, RT, getSigFigString} from "./cct_globals";
import { bin } from 'd3-array';
import Forest  from './cct_repr';
import { leastIndex } from "d3";

class Model{
    constructor(){
        this._observers = makeSignaller();

        //initialize default data and state
        this.data = {
                        "trees":[],
                        "legends": ["Unified", "Individual"],
                        "colors": ["Default", "Inverted"],
                        "forestData": null,
                        "rootNodeNames": ["Show all trees"],
                        "currentStrictness": 1.5,
                        "distCounts":[],
                        "maxHeight": 0,
                        "removedNodes": []
                    };

        this.state = {
                        "selectedNodes":[], 
                        "collapsedNodes":[],
                        "primaryMetric": null,
                        "secondaryMetric": null,
                        "lastClicked": null,
                        "legend": 0,
                        "colorScheme": 0,
                        "legendText": this.data.legends[0],
                        "colorText": this.data.colors[0],
                        "brushOn": -1,
                        "hierarchyUpdated": true,
                        "cachedThreshold": 0,
                        "outlierThreshold": 0,
                        "pruneEnabled": false,
                        "metricUpdated": true
                    };

        //setup model
        RT['jsNodeSelected'] = 'MATCH (\\"*\\")->(a) WHERE a.\\"name\\" IS NOT NONE';
        let cleanTree = RT["hatchet_tree_def"];
        let _forestData = JSON.parse(cleanTree);
        this.forest = new Forest(_forestData);

        // // pick the first metric listed to color the nodes
        this.state.primaryMetric = this.forest.metricColumns[0];
        this.state.secondaryMetric = this.forest.metricColumns[1];
        this.state.activeTree = "Show all trees";
        this.state.treeXOffsets = [];
        this.state.lastClicked = this.forest.getCurrentTree(0);
        this.state.prune_range = {"low": Number.MAX_SAFE_INTEGER, "high": Number.MIN_SAFE_INTEGER};
        //prunes away non-internal zero nodes
        this.forest.initializePrunedTrees(this.state.primaryMetric);
    }

    // --------------------------------------------
    // Node selection helper functions
    // --------------------------------------------

    _initializePruneRange(bins){
        bins.forEach(d=>{
            this.state.prune_range["low"] = Math.min(d.x0, this.state.prune_range[0]);
            this.state.prune_range["high"] = Math.max(d.x1, this.state.prune_range[1]);
        });
    }

    _printNodeData(nodeList) {
        /**
             * To pretty print the node data as a IPython table
             * 
             * @param {Array} nodeList - An array of selected nodes for formatting
             */
        
        var nodeStr = '<table><tr><td>name</td>';
        var numNodes = nodeList.length;
        var metricColumns = this.forest["metricColumns"];

        //lay the nodes out in a table
        for (let i = 0; i < metricColumns.length; i++) {
            nodeStr += '<td>' + metricColumns[i] + '</td>';
        }
        nodeStr += '</tr>';
        for (let i = 0; i < numNodes; i++) {
            nodeStr += "<tr>"
            for (var j = 0; j < metricColumns.length; j++) {
                if (j == 0) {
                    if(nodeList[i].data.aggregate){
                        if (nodeList[i].data.elided.length == 1){
                            nodeStr += `<td>${nodeList[i].data.prototype.data.name} Subtree </td>`
                        }
                        else if(nodeList[i].data.elided.length > 1){
                            nodeStr += `<td>Children of: ${nodeList[i].parent.data.name} </td>`
                        }
                    }
                    else{
                        nodeStr += `<td>${nodeList[i].data.name}</td>`;
                    }
                }
                if (nodeList[i].data.aggregateMetrics){
                    nodeStr += `<td>${getSigFigString(nodeList[i].data.aggregateMetrics[metricColumns[j]])}</td>`
                }
                else{
                    nodeStr += `<td>${getSigFigString(nodeList[i].data.metrics[metricColumns[j]])}</td>`
                }
            }
            nodeStr += '</tr>'
        }
        nodeStr = nodeStr + '</table>';

        return nodeStr;
    }


    _printQuery(nodeList, exclude) {
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

        // do some evaluation for other subtrees
        // we could generate python code that does this
        var queryStr = '<no query generated>';


        // let conditions = ''


        // let queryStr = `MATCH (n)
        //             WHERE ${conditions}`;

        

        if(!leftMostNode.data.aggregate && !rightMostNode.data.aggregate){
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

        }

        return queryStr;
    }



    register(s){
        /**
         * Registers a signaller (a callback function) to be run with _observers.notify()
         * 
         * @param {Function} s - (a callback function) to be run with _observers.notify()
         */
        this._observers.add(s, "model");
    }

    updateBins(numBins){
        let nodes = []
        this.state.numBins = numBins;
        if(this.data.distCounts.length != numBins){
            for(let t of this.forest.getTrees()){
                nodes = nodes.concat(t.descendants().filter(x=>{return x.data.metrics != undefined})); 
            }
        }

        let bins = bin().value(d=>d.data.metrics[this.state.primaryMetric]).thresholds(numBins); 
        let bin_dist = bins(nodes);
        let zero_cnts = new Array(bin_dist.length).fill().map(d=>([]));
        let b = 0;

        let x0 = bin_dist[b].x0;
        let x1 = bin_dist[b].x1;
        bin_dist[b] = bin_dist[b].filter((value)=>{
            return value.data.metrics[this.state.primaryMetric] != 0;
        })

        bin_dist[b]['x0'] = x0;
        bin_dist[b]['x1'] = x1;

        //store zero metric internal nodes
        for(let bn in bin_dist){
            let parent = null;
            for(let n of bin_dist[bn]){
                parent = n.parent;
                while(parent !== null){
                    if(zero_cnts[bn].some(node => { return node.data.id == parent.data.id })){
                        break;
                    }
                    else if(parent.data.metrics[this.state.primaryMetric] == 0){
                        zero_cnts[bn].push(parent);
                    }
                    parent = parent.parent;
                }
            }
            zero_cnts[bn].x0 = bin_dist[bn].x0;
            zero_cnts[bn].x1 = bin_dist[bn].x1;
        }

        if(this.state.prune_range["low"] === Number.MAX_SAFE_INTEGER){
            this._initializePruneRange(bin_dist);
        }

        this.data.distCounts = {"nonzero": bin_dist, "internalzero": zero_cnts};
    }

    enablePruneTree(threshold){
        /**
         * Enables/disables the mass prune tree functionality.
         * Prunes tree on click based on current slider position.
         * 1.5 by default from view.
         * 
         * @param {bool} enabled - Switch bool that guides if we disable or enable mass pruning
         * @param {float} threshold - User defined strictness of pruning. Used as the multiplier in set outlier flags.
         *      On first click this will be 1.5.
         */

        this.state.pruneEnabled = !this.state.pruneEnabled;
        // if (this.state.pruneEnabled){
        //     this.data.currentStrictness = threshold;
        //     this.forest.aggregateTreeData(this.state.primaryMetric, threshold, "FlagOutliers");
        //     this.state.hierarchyUpdated = true;
        // } 
        
        this._observers.notify();
        
    }

    _setZeroFlags(){
        /**
         * Reurns a call back function which
         * flags all subtrees that
         * only contains zero values.
         */
        return (h, primaryMetric)=>{
            h.each(function(node){
                var metric = node.data.metrics[primaryMetric];
                if(metric != 0){
                    node.data.show = 1;
                }
                else{
                    node.data.show = 0;
                }
            })
        }
    }

    _setRangeFlags(){
        /**
         * Sets a show flag when a metric is inside of the provided range.
         */
        const mdl = this;

        return (tree, primaryMetric) => {
            tree.each((node)=>{
                var metric = node.data.metrics[primaryMetric];
                if(metric == 0){
                    node.data.show = 0
                }
                else if(metric >= mdl.state.prune_range.low && metric <= mdl.state.prune_range.high){
                    node.data.show = 1;
                }
                else{
                    node.data.show = 0;
                }
            })        
        }
    }

    _setOutlierFlags(){
        /**
         * Sets outlier flags on a d3 hierarchy of call sites.
         * An outlier is defined as outside of the range between
         * the IQR*(a user defined scalar) + 75th quantile and
         * 25th quantile - IQR*(scalar). 
         * 
         * @param {Hierarchy} h - A d3 hierarchy containg metric values
         */
        const mdl = this;

        return (h, primaryMetric) => {
            var outlierScalar = mdl.data.currentStrictness;
            var upperOutlierThreshold = Number.MAX_VALUE;
            var lowerOutlierThreshold = Number.MIN_VALUE;

            var metrics = mdl.forest._getListOfMetrics(h, primaryMetric);
            var IQR = mdl.forest.stats._getIQR(metrics, primaryMetric);

            if(!isNaN(IQR)){
                upperOutlierThreshold = mdl.forest.stats._quantile(metrics, .75, primaryMetric) + (IQR * outlierScalar);
                lowerOutlierThreshold = mdl.forest.stats._quantile(metrics, .25, primaryMetric) - (IQR * outlierScalar);
            } 

            h.each(function(node){
                var metric = node.data.metrics[primaryMetric];
                if( metric >= upperOutlierThreshold || 
                    metric <= lowerOutlierThreshold){
                    node.data.show = 1;
                }
                else{
                    node.data.show = 0;
                }
            })
        }
    }

    pruneTree(threshold){
        /**
         * Interface to the private tree aggregation functions.
         *  Calls when user adjusts automatic pruning slider.
         * 
         * @param {float} threshold - User defined strictness of pruning. Used as the multiplier in set outlier flags.
         */
        this.data.currentStrictness = threshold;
        this.forest.aggregateTreeData(this.state.primaryMetric, this._setRangeFlags());
        this.state.hierarchyUpdated = true;

        this._observers.notify();
    }

    updateSelected(nodes){
        /**
         * Updates which nodes are "Selected" by the user in the model
         *
         * @param {Array} nodes - A list of selected nodes
         */
        this.state['selectedNodes'] = nodes;
        this.updateTooltip(nodes);

        // if(nodes.length > 0 && nodes[0]){
        //     RT['jsNodeSelected'] = JSON.stringify(this._printQuery(nodes));
        // } else {
        //     RT['jsNodeSelected'] = JSON.stringify(["*"]);
        // }

        this._observers.notify();
    }

    handleDoubleClick(d){
        /**
         * Manages the collapsing and expanding of subtrees
         *  when a user is manually pruning or exploring a tree.
         * 
         * @param {node} d - The node the user just double clicked.
         *      Can be a surrogate or real node.
         */
        //hiding a subtree
        if(!d.data.aggregate){
            if(d.parent){
                //main manipulation is in parent scope
                let children = d.parent.children;

                if(!d.parent._children){
                    d.parent._children = [];
                }

                d.parent._children.push(d);
                let dummy = this.forest._buildDummyHolder(d, d.parent, [d]);
                let swapIndex = d.parent.children.indexOf(d);
                children[swapIndex] = dummy;
            }
        } 

        // Expanding a dummy node 
        // Replaces a node if one was elided
        // Appends if multiple were elided
        else{
            if(d.data.elided.length == 1){
                // patch that clears aggregate metrics upon doubleclick
                let insIndex = d.parent.children.indexOf(d);
                d.parent.children[insIndex] = d.data.prototype;
            }
            else{
                for(let elided of d.data.elided){
                    delete elided.data.aggregateMetrics;
                    let delIndex = d.parent._children.indexOf(elided);
                    d.parent._children.splice(delIndex, 1);

                    d.parent.children.push(elided);
                }
                d.parent.children = d.parent.children.filter(child => child !== d);
            }
        }

        this.state["lastClicked"] = d;

        this.state.hierarchyUpdated = true;
        this._observers.notify();
    }

    handleNodeComposition(node){
        /**
         * Function which re-arranges the tree to compose
         * a nodes with its parent.
         * Warning: There are bugs in this function.
         */
        let children = node.children
        let parent = node.parent;
        let tpar;

        if(node.data.true_parent === undefined){
            tpar = node.parent;
            node.data.true_parent = node.parent;
        }
        else{
            tpar = node.data.true_parent;
        }


        let index = parent.children.indexOf(node);
        parent.children.splice(index, 1);

        if(tpar.data.composed == undefined){
            tpar.data.composed = [];
        }
        tpar.data.composed.push(node);

        if(children != undefined && children.length > 0){
            for(let child of children){
                child.data.true_parent = child.parent;
                child.each(n=>{
                    n.depth--;
                })
                child.parent = parent;
            }
            parent.children = parent.children.concat(children);
        }

        if(parent.children.length == 0){
            delete parent.children;
        }

        //this is for querying
        this.data.removedNodes.push(node);

        this.state.hierarchyUpdated = true;
        this._observers.notify();
    }

    handleNodeDecomposition(node){
        /**
         * Function which manages decomposing 
         * a node from its parent.
         */
        let ndx = null;

        node.each(n=>{
            if(n.data.composed !== undefined){
                for(let comp of n.data.composed){
                    for(let cmpchild of comp.children){
                        ndx = n.children.indexOf(cmpchild);
                        n.children.splice(ndx, 1);
                    }
                    n.children.push(comp);
                    comp.parent = comp.data.true_parent;
                    delete comp.data.true_parent;
                }
                delete n.data.composed;
            }
            n.depth = n.parent.depth+1;
        })

        this.state.hierarchyUpdated = true;
        this._observers.notify();
    }
    

    toggleBrush(){
        /**
         * Toggles the brushing functionality with a button click
         *
         */

        this.state["brushOn"] = -this.state["brushOn"];
        this._observers.notify();
    }

    setBrushedPoints(selection){
        /**
         * Calculates which nodes are in the brushing area.
         * 
         * @param {Array} selection - Selected nodes
         *
         */

        if(selection){
            this.updateSelected(selection);
        }
        else{
            this.updateSelected([]);
        }
        
    }

    updateTooltip(nodes){
        /**
         * Updates the model with new tooltip information based on user selection
         * 
         * @param {Array} nodes - A list of selected nodes
         *
         */
        if(nodes.length > 0 && nodes[0]){
            var longestName = 0;
            nodes.forEach(function (d) {
                if(!d.data.aggregate){
                    var nodeData = d.data.frame.name + ': ' + d.data.metrics.time + 's (' + d.data.metrics["time (inc)"] + 's inc)';
                }
                else{
                    var nodeData = d.data.prototype.data.frame.name + ': ' + d.data.aggregateMetrics.time + 's (' + d.data.aggregateMetrics["time (inc)"] + 's inc)';
                }
                longestName = Math.max(nodeData.length, longestName);
            });
            this.data["tipText"] = this._printNodeData(nodes);
        } 
        else{
            this.data["tipText"] = '<p>Click a node or "Select nodes" to see more info</p>';
        }
    }

    changeMetric(newMetric, source){
            /**
         * Changes the currently selected metric in the model.
         * 
         * @param {String} newMetric - the most recently selected metric
         *
         */

        if(source.includes("primary")){
            this.state.primaryMetric = newMetric;
        } 
        else if(source.includes("secondary")){
            this.state.secondaryMetric = newMetric;
        }
        
        if(source.includes("primary")){
            if(this.state.pruneEnabled){
                this.forest.resetMutable();
                this.state.hierarchyUpdated = true;
            }

            this.state.metricUpdated = true;
            this.updateBins(this.state.numBins);
            this.state.prune_range.low = this.data.distCounts.nonzero[0].x0;
            this.state.prune_range.high = this.data.distCounts.nonzero[this.data.distCounts.nonzero.length-1].x1;

        }

        this._observers.notify();
    }
    
    changeColorScheme(v){
        /**
         * Changes the current color scheme to inverse or regular. Updates the view
         *
         */

        //loop through the possible color schemes
        this.state["colorScheme"] = this.data["colors"].indexOf(v);
        this.state["colorText"] = v;
        this._observers.notify();
    }

    updateLegends(v){
        /**
         * Toggles between divergent or unified legends. Updates the view
         *
         */
        //loop through legend configruations
        this.state["legend"] = this.data["legends"].indexOf(v);
        this.state["legendText"] = v;
        this._observers.notify();
    }

    updateActiveTrees(activeTree){
        /**
         * Sets which tree is currently "active" in the model. Updates the view.
         *
         */
        this.state["activeTree"] = activeTree;
        this._observers.notify();
    }

    updatePruneRange(low, high){
        /**
         * Updates the inclusive range of metrics
         *  which are not to be pruned away.
         *  Additionally, prunes and aggregates trees.
         */
        this.state.prune_range.low = low;
        this.state.prune_range.high = high;

        this.forest.aggregateTreeData(this.state.primaryMetric, (h, primaryMetric)=>{
            h.each(function(node){
                var metric = node.data.metrics[primaryMetric];
                if(metric != 0){
                    node.data.show = 1;
                }
                else{
                    node.data.show = 0;
                }
            })
        });

        this.forest.aggregateTreeData(this.state.primaryMetric, this._setRangeFlags());

        this.state.hierarchyUpdated = true;
        
        this._observers.notify();
    }

    resetView(){
        /**
         * Function that sets a flag which causes the 
         * view to reset all trees to their original layouts.
         */
        this.state.resetView = true;
        this._observers.notify();
    }

    toggleMenuActive(){
        /**
         * Set a global flag indicating if the menu was
         *  clicked on or off.
         */
        this.state.menu_active = !this.state.menu_active;
        this._observers.notify();
    }


    storeSnapshotQuery(){
        /**
         * Stores a snapshot description of the tree 
         * as a query in a roundtrip variable.
         */
        let leaves = []
        for(let tree of this.forest.getTrees()){
            leaves = leaves.concat(tree.leaves()); 
        }

        let norms = leaves.filter((n)=>{return !n.data.aggregate});
        let aggs = leaves.filter((n)=>{return n.data.aggregate});

        norms = norms.concat(aggs);

        console.log(norms);

        let full_query = '';

        //inclusive query
        let path_query = `MATCH (\\"*\\")->(n) `;
        let initial_flag = true;
        for(const leaf of norms){
            if(initial_flag){
                if(leaf.data.aggregate){
                    path_query += `WHERE n.\\"node_id\\" = ${leaf.data.prototype.data.metrics._hatchet_nid}`;
                }
                else{
                    path_query += `WHERE n.\\"node_id\\" = ${leaf.data.metrics._hatchet_nid}`;
                }
                initial_flag = false;
            }
            else{
                path_query += ` OR n.\\"node_id\\" = ${leaf.data.metrics._hatchet_nid}`;
            }
        }


        full_query=`${path_query}`


        if(this.data.removedNodes.length > 0){
            //exclusive query
            initial_flag = true;
            let ex_query = 'MATCH (r) ' 
            for(const node of this.data.removedNodes){
                if(initial_flag){
                    ex_query += `WHERE NOT r.\\"node_id\\" = ${node.data.metrics._hatchet_nid}`;
                    initial_flag = false;
                }
                else{
                    ex_query += ` AND NOT r.\\"node_id\\" = ${node.data.metrics._hatchet_nid}`;
                }
            }

            full_query=`{${path_query}} AND {${ex_query}}`
        }

        RT['jsNodeSelected'] = full_query;
        
    }

}


export default Model;