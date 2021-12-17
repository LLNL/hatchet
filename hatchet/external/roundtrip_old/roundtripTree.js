
//d3.v4
(function (element) {
    require(['https://d3js.org/d3.v4.min.js'], function (d3) {
        const globals = Object.freeze({
            UNIFIED: 0,
            DEFAULT: 0,
            signals: {
                CLICK: "CLICK",
                DBLCLICK: "DBLCLICK",
                BRUSH: "BRUSH",
                TOGGLEBRUSH: "TOGGLEBRUSH",
                COLLAPSE: "COLLAPSE",
                METRICCHANGE: "METRICCHANGE",
                TREECHANGE: "TREECHANGE",
                COLORCLICK: "COLORCLICK",
                LEGENDCLICK: "LEGENDCLICK",
                ZOOM: "ZOOM"
            },
            layout: {
                margin: {top: 20, right: 20, bottom: 20, left: 20},
            },
            duration: 750,
            treeHeight: 300
        });

        jsNodeSelected = "['*']";

        var makeColorManager = function(model){
            
            var _regularColors = [
                ['#006d2c', '#31a354', '#74c476', '#a1d99b', '#c7e9c0', '#edf8e9'], //green
                ['#a50f15', '#de2d26', '#fb6a4a', '#fc9272', '#fcbba1', '#fee5d9'], //red
                ['#08519c', '#3182bd', '#6baed6', '#9ecae1', '#c6dbef', '#eff3ff'], //blue
                ['#54278f', '#756bb1', '#9e9ac8', '#bcbddc', '#dadaeb', '#f2f0f7'], //purple
                ['#a63603', '#e6550d', '#fd8d3c', '#fdae6b', '#fdd0a2', '#feedde'], //orange
                ['#252525', '#636363', '#969696', '#bdbdbd', '#d9d9d9', '#f7f7f7']]; //black

            var _invertColors = [
                ['#edf8e9', '#c7e9c0', '#a1d99b', '#74c476', '#31a354', '#006d2c'], //green
                ['#fee5d9', '#fcbba1', '#fc9272', '#fb6a4a', '#de2d26', '#a50f15'], //red
                ['#eff3ff', '#c6dbef', '#9ecae1', '#6baed6', '#3182bd', '#08519c'], //blue
                ['#f2f0f7', '#dadaeb', '#bcbddc', '#9e9ac8', '#756bb1', '#54278f'], //purple
                ['#feedde', '#fdd0a2', '#fdae6b', '#fd8d3c', '#e6550d', '#a63603'], //orange
                ['#f7f7f7', '#d9d9d9', '#bdbdbd', '#969696', '#636363', '#252525']];  //black
            
        
            var _allTreesColors = ['#d73027', '#fc8d59', '#fee090', '#e0f3f8', '#91bfdb', '#4575b4'];
            var _invertedAllTreesColors = ['#4575b4', '#91bfdb', '#e0f3f8', '#fee090', '#fc8d59', '#d73027'];

            let _state = model.state;
            let _forestMinMax = model.data["forestMinMax"];
            let _modelForestStats = model.data["forestStats"];

            return {
                setColors: function(treeIndex){
                    /**
                     * Sets the color pallet per tree to be either inverse or regular or unified/unique to each tree
                     * 
                     * @param {Int} treeIndex - The index of the current tree's colors being set
                     */

                    var colorSchemeUsed;
    
                    if (treeIndex == -1) { //all trees are displayed
                        if (_state["colorScheme"] == 0) {
                            colorSchemeUsed = _allTreesColors;
                        } else {
                            colorSchemeUsed = _invertedAllTreesColors;
                        }
                    } 
                    else { //single tree is displayed
                        if (_state["colorScheme"] == 0) {
                            colorSchemeUsed = _regularColors[treeIndex];
                        } else {
                            colorSchemeUsed = _invertColors[treeIndex];
                        }
                    }
    
                    return colorSchemeUsed;
                },
                getLegendDomains: function(treeIndex){
                    /**
                     * Sets the min and max of the legend. 
                     * 
                     * @param {Int} treeIndex - The index of the current tree's legend being set
                     */

                    var colorScaleDomain;
                    var metricRange;
                    var curMetric = _state["selectedMetric"];
                    
                    // so hacky: need to fix later
                    if (model.data["legends"][_state["legend"]].includes("Unified")) {
                        treeIndex = -1;
                    }

                    if (treeIndex == -1) { //unified color legend
                        metricRange = _forestMinMax[curMetric].max - _forestMinMax[curMetric].min;
                        colorScaleDomain = [0, 0.1, 0.3, 0.5, 0.7, 0.9, 1].map(function (x) {
                            return x * metricRange + _forestMinMax[curMetric].min;
                        });
                    } 
                    else{
                        metricRange = _modelForestStats[treeIndex][curMetric].max - _modelForestStats[treeIndex][curMetric].min;
                        colorScaleDomain = [0, 0.1, 0.3, 0.5, 0.7, 0.9, 1].map(function (x) {
                            return x * metricRange + _modelForestStats[treeIndex][curMetric].min;
                        });
                    }

                    return colorScaleDomain;
                },
                getColorLegend: function(treeIndex) {
                    /**
                     * Gets the color scheme used for a legend, contigent on individual tree-specific schemes or one unified color scheme.
                     * 
                     * @param {Int} treeIndex - The index of the current tree's legend being set
                     */
                
                    //hacky need to fix later
                    if (model.data["legends"][_state["legend"]].includes("Unified")) {
                        treeIndex = -1;
                    }

                    if (treeIndex == -1) { //unified color legend
                        var colorSchemeUsed = this.setColors(treeIndex);
    
                    } else {
                        var colorSchemeUsed = this.setColors(treeIndex);
                    }
                    return colorSchemeUsed;
                },
                calcColorScale: function(nodeMetric, treeIndex) {
                    /**
                     * Calculates the bins for the color scheme based on the current, user-selected metric.
                     * 
                     * @param {String} nodeMetric - the name of the current metric being mapped to a color range
                     * @param {Int} treeIndex - The index of the current tree's legend being set
                     */

                    var curMetric = d3.select(element).select('#metricSelect').property('value');
                    var colorSchemeUsed = this.setColors(treeIndex);
                    
                    if (treeIndex == -1) {
                        var metric_range = _forestMinMax[curMetric].max - _forestMinMax[curMetric].min;
                        var proportion_of_total = (nodeMetric - _forestMinMax[curMetric].min) / metric_range;
                    } else {
                        var metric_range = _modelForestStats[treeIndex][curMetric].max - _modelForestStats[treeIndex][curMetric].min;
                        var proportion_of_total = nodeMetric / 1;
    
                        if (metric_range != 0) {
                            proportion_of_total = (nodeMetric - _modelForestStats[treeIndex][curMetric].min) / metric_range;
                        }
                    }
    
                    if (proportion_of_total > 0.9) {
                        return colorSchemeUsed[0];
                    }
                    if (proportion_of_total > 0.7) {
                        return colorSchemeUsed[1];
                    }
                    if (proportion_of_total > 0.5) {
                        return colorSchemeUsed[2];
                    }
                    if (proportion_of_total > 0.3) {
                        return colorSchemeUsed[3];
                    }
                    if (proportion_of_total > 0.1) {
                        return colorSchemeUsed[4];
                    } else {
                        return colorSchemeUsed[5];
                    }
                }

            }
        }
        
        // This is the makeSignaller from class
        var makeSignaller = function() {
            let _subscribers = []; // Private member

            // Return the object that's created
            return {
                // Register a function with the notification system
                add: function(handlerFunction) {_subscribers.push(handlerFunction); },

                // Loop through all registered function and call them with passed
                // arguments
                notify: function(args) {
                    for (var i = 0; i < _subscribers.length; i++) {
                        _subscribers[i](args);
                    }
                }
            };
        }

        // Create an object that handles user interaction and events
        var createController = function(model) {
            var _model = model;

            return {
                // All types of events run through a central dispatch
                // function. The dispatch function decides what to do.
                dispatch: function(evt) {
                    switch(evt.type) {
                        case (globals.signals.CLICK):
                            _model.updateSelected([evt.node]);
                            break;
                        case (globals.signals.DBLCLICK):
                            _model.handleDoubleClick(evt.node,evt.tree);
                            break;
                        case(globals.signals.TOGGLEBRUSH):
                            _model.toggleBrush();
                            break;
                        case (globals.signals.BRUSH):
                            _model.setBrushedPoints(evt.selection, evt.end);
                            break;
                        case (globals.signals.METRICCHANGE):
                            _model.changeMetric(evt.newMetric);
                            break;
                        case(globals.signals.COLORCLICK):
                            _model.changeColorScheme();
                            break;
                        case(globals.signals.TREECHANGE):
                            _model.updateActiveTrees(evt.display);
                            break;
                        case(globals.signals.LEGENDCLICK):
                            _model.updateLegends();
                            break;
                        case(globals.signals.ZOOM):
                            _model.updateNodeLocations(evt.index, evt.transformation);
                            break;
                        default:
                            console.log('Unknown event type', evt.type);
                    }
                }
            };
        }


        var createModel = function(){
            var _observers = makeSignaller();
            
            //initialize default data and state
            var _data = {
                            "trees":[],
                            "legends": ["Unified", "Indiv."],
                            "colors": ["Default", "Inverted"],
                            "forestData": null,
                            "rootNodeNames": [],
                            "numberOfTrees": 0,
                            "metricColumns": [],
                            "forestMinMax": [],
                            "forestStats": []
                        };

            var _state = {
                            "selectedNodes":[], 
                            "collapsedNodes":[],
                            "selectedMetric": [],
                            "lastClicked": null,
                            "legend": 0,
                            "colorScheme": 0,
                            "brushOn": -1
                        };

            //setup model
            var cleanTree = argList[0].replace(/'/g, '"');
            
            _data["forestData"] = JSON.parse(cleanTree);
            _data["rootNodeNames"].push("Show all trees");
            _data["numberOfTrees"] = _data["forestData"].length;
            _data["metricColumns"] = d3.keys(_data["forestData"][0].metrics);

            // pick the first metric listed to color the nodes
            _state["selectedMetric"] = _data["metricColumns"][0];
            _state["lastClicked"] = d3.hierarchy(_data["forestData"][0], d => d.children)
            _state["activeTree"] = "Show all trees";
            
            //forest stats holds statistical descriptions of
            // the metrics on each tree in the forest
            var _forestStats = [];
            var _forestMinMax = {}; 
            for (var i = 0; i < _data["numberOfTrees"]; i++) {
                var thisTree = _data["forestData"][i];

                // Get tree names for the display select options
                _data["rootNodeNames"].push(thisTree.frame.name);

                var thisTreeMetrics = {};

                // init the min/max for all trees' metricColumns
                for(let d of _data["metricColumns"]){
                    thisTreeMetrics[d] = {
                        "min": Number.MAX_VALUE,
                        "max": Number.MIN_VALUE
                    }
                }

                _forestStats.push(thisTreeMetrics);
            }

            for(let d of _data["metricColumns"]) {
                _forestMinMax[d] = {
                "min": Number.MAX_VALUE,
                "max": Number.MIN_VALUE
                }
            }

            _data["forestMinMax"] = _forestMinMax;
            _data["forestStats"] = _forestStats;

            // HELPER FUNCTION DEFINTIONS
            function _printNodeData(nodeList) {
                /**
                  * To pretty print the node data as a IPython table
                  * 
                  * @param {Array} nodeList - An array of selected nodes for formatting
                  */
                
                var nodeStr = '<table><tr><td>name</td>';
                var numNodes = nodeList.length;
                var metricColumns = model.data["metricColumns"];

                //lay the nodes out in a table
                for (var i = 0; i < metricColumns.length; i++) {
                    nodeStr += '<td>' + metricColumns[i] + '</td>';
                }
                nodeStr += '</tr>';
                for (var i = 0; i < numNodes; i++) {
                    for (var j = 0; j < metricColumns.length; j++) {
                        if (j == 0) {
                            nodeStr += '<tr><td>' + nodeList[i].data.frame.name + '</td><td>' + nodeList[i].data.metrics[metricColumns[j]] + '</td><td>';
                        }
                        else if (j == metricColumns.length - 1) {
                            nodeStr += nodeList[i].data.metrics[metricColumns[j]] + '</td></tr>';
                        }
                        else {
                            nodeStr += nodeList[i].data.metrics[metricColumns[j]];
                        }
                    }
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
                var lastNode = "";
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
                var queryStr = "['<no query generated>']";
                if ((nodeList.length > 1) && (selectionIsAChain)) {
                    // This query is for chains
                    queryStr = "[{'name': '" + leftMostNode.data.frame.name + "'}, '*', {'name': '" + rightMostNode.data.frame.name + "'}]";
                }
                else if (nodeList.length > 1) {
                    // This query is for subtrees
                    queryStr = "[{'name': '" + leftMostNode.data.frame.name + "'}, '*', {'depth': '<= " + rightMostNode.depth + "' }]";
                }
                else {
                    //Single node query
                    queryStr = "[{'name': '" + leftMostNode.data.frame.name + "'}]";
                }

                return queryStr;
            }


            /* Class object created from call to createModel */
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
                addTree: function(tm){
                    /**
                     * Pushes a tree into the model.
                     * 
                     * @param {Object} tm - A d3 tree constructed from a d3 hierarchy
                     */

                    _data['trees'].push(tm);
                },
                getTree: function(index){
                    /**
                     * Retrieves a tree from the model.
                     * 
                     * @param {Number} index - The index of the tree we want to get
                     */
                    return _data['trees'][index];
                },
                getNodesFromMap: function(index){
                    /**
                     * Retrieves tree nodes from the model
                     * 
                     * @param {Number} index - The index of the tree nodes we want to get
                     */
                    return _data['trees'][index].descendants();
                },
                getLinksFromMap: function(index){
                    /**
                     * Retrieves tree links from the model
                     * 
                     * @param {Number} index - The index of the tree links we want to get
                     */
                    return _data['trees'][index].descendants().slice(1);
                },
                updateNodes: function(index, f){
                    /**
                     * Updates the nodes in the model according to the passed in callback function.
                     *
                     * @param {Number} index - The index of the tree we are updating
                     * @param {Function} f - The callback function being applied to the nodes
                     */
                    f(_data['trees'][index].descendants());
                },
                updateforestStats: function(index){
                    /**
                     * Updates the local maximum and minimum metrics for a single tree in the forest. 
                     * Updates the global maximum and minimum metrics across all trees in our forest.
                     * Stores these values in the model.
                     *
                     * @param {Number} index - The index of the tree we are updating
                     */

                    var curTreeData = _forestStats[index];
                    for(let metric of  _data["metricColumns"]) {
                        //get local minimum and maximum for our current tree
                        // for each metric
                        _data['trees'][index].descendants().forEach(function (d) {
                            curTreeData[metric].max = Math.max(curTreeData[metric].max, d.data.metrics[metric]);
                            curTreeData[metric].min = Math.min(curTreeData[metric].min, d.data.metrics[metric]);
                        });

                        //Update global minimum and maximum per metric
                        _forestMinMax[metric].max = Math.max(_forestMinMax[metric].max, curTreeData[metric].max);
                        _forestMinMax[metric].min = Math.min(_forestMinMax[metric].min, curTreeData[metric].min);
                    }

                    _data["forestStats"] = _forestStats;
                    _data["forestMinMax"] = _forestMinMax;
                },
                updateSelected: function(nodes){
                    /**
                     * Updates which nodes are "Selected" by the user in the model
                     *
                     * @param {Array} nodes - A list of selected nodes
                     */

                    _state['selectedNodes'] = nodes;
                    this.updateTooltip(nodes);

                    if(nodes.length > 0){
                        jsNodeSelected = _printQuery(nodes);
                    } else {
                        jsNodeSelected = "['*']";
                    }
                    
                    _observers.notify();
                },
                handleDoubleClick: function(d){
                    /**
                     * Handles the model functionlaity of hiding and un-hiding subtrees
                     * on double click
                     *
                     * @param {Object} d - The node which was double clicked
                     */

                    // if the node is not already collapsed
                    // keep track of collapsed nodes
                    if (! _state["collapsedNodes"].includes(d) ){
                        _state["collapsedNodes"].push(d);
                    }
                    else{
                        index = _state["collapsedNodes"].indexOf(d);
                        _state["collapsedNodes"].splice(index, 1);
                    }

                    //this is kind of a hack for this paradigm
                    // but it updates the passed data directly
                    // and hides children nodes triggering update
                    // when view is re-rendered
                    if (d.children) {
                        d._children = d.children;
                        d.children = null;
                    } else {
                        d.children = d._children;
                        d._children = null;
                    }

                    _state["lastClicked"] = d;
                    
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
                setBrushedPoints(selection, end){
                    /**
                     * Calculates which nodes are in the brushing area.
                     * 
                     * @param {Array} selection - A d3 selection matrix with svg coordinates showing the selected space
                     * @param {Boolean} end - A variable which tests if the brushing is over or not
                     *
                     */

                    var brushedNodes = [];

                    if(selection){
                        //calculate brushed points
                        for(var i = 0; i < _data["numberOfTrees"]; i++){
                            nodes = _data['trees'][i].descendants();
                            nodes.forEach(function(d){
                                if(selection[0][0] <= d.yMainG && selection[1][0] >= d.yMainG 
                                    && selection[0][1] <= d.xMainG && selection[1][1] >= d.xMainG){
                                    brushedNodes.push(d);
                                }
                            })
                        }

                        //update if end
                        if(end){
                            //call update selected
                            this.updateSelected(brushedNodes);
                        }
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

                    if(nodes.length > 0){
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
                changeMetric: function(newMetric){
                    /**
                     * Changes the currently selected metric in the model.
                     * 
                     * @param {String} newMetric - the most recently selected metric
                     *
                     */

                    _state["selectedMetric"] = newMetric;
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
                updateNodeLocations: function(index, transformation){
                    /**
                     * Transforms the x and y values of nodes based on transformations
                     * applied to their parent group
                     * 
                     * @param {Number} index - Index of the tree who's nodes are being updated
                     * @param {Object} transformation - The current transformation matrix (CTM) of an parent group
                     *
                     */
                    _data["trees"][index].descendants().forEach(function(d, i) {
                        // This function gets the absolute location for each point based on the relative
                        // locations of the points based on transformations
                        // the margins were being added into the .e and .f values so they have to be subtracted
                        // I think they come from the margins being added into the "main group" when it is created
                        // We can brush regardless of zoom or pan
                        // Adapted from: https://stackoverflow.com/questions/18554224/getting-screen-positions-of-d3-nodes-after-transform
                        d.yMainG = transformation.e + d.y0*transformation.d + d.x0*transformation.c - globals.layout.margin.left;
                        d.xMainG = transformation.f + d.y0*transformation.b + d.x0*transformation.a - globals.layout.margin.top;
                    });
                }
            }
        }

        var createMenuView = function(elem, model){
            /**
             * View class for the menu portion of the visualization
             * 
             * @param {DOMElement} elem - The current cell of the calling jupyter notebook
             * @param {Model} model - The model object
             */

            let _observers = makeSignaller();
            var rootNodeNames = model.data["rootNodeNames"];
            var metricColumns = model.data["metricColumns"];
            var brushOn = model.state["brushOn"];

                 
            //initialize bounds for svg
            var width = element.clientWidth - globals.layout.margin.right - globals.layout.margin.left;
            var height = globals.treeHeight * (model.data["numberOfTrees"] + 1);

            // ----------------------------------------------
            // Create HTML interactables
            // ----------------------------------------------
            const htmlInputs = d3.select(elem).insert('div', '.canvas').attr('class','html-inputs');

            htmlInputs.append('label').attr('for', 'metricSelect').text('Color by:');
            var metricInput = htmlInputs.append("select") //element
                    .attr("id", "metricSelect")
                    .selectAll('option')
                    .data(metricColumns)
                    .enter()
                    .append('option')
                    .text(d => d)
                    .attr('value', d => d);
            document.getElementById("metricSelect").style.margin = "10px 10px 10px 0px";

            htmlInputs.append('label').style('margin', '0 0 0 10px').attr('for', 'treeRootSelect').text(' Display:');
            var treeRootInput = htmlInputs.append("select") //element
                    .attr("id", "treeRootSelect")
                    .selectAll('option')
                    .data(rootNodeNames)
                    .enter()
                    .append('option')
                    .attr('selected', d => d.includes('Show all trees') ? "selected" : null)
                    .text(d => d)
                    .attr('value', (d, i) => i + "|" + d);

            document.getElementById("treeRootSelect").style.margin = "10px 10px 10px 10px";

            d3.select(elem).select('#treeRootSelect')
                    .on('change', function () {
                        _observers.notify({
                            type: globals.signals.TREECHANGE,
                            display: this.value
                        });
                    });
            
            // ----------------------------------------------
            // Create SVG and SVG-based interactables
            // ----------------------------------------------

            //make an svg in the scope of the current
            // element/drawing space
            var _svg = d3.select(elem).append('svg').attr('class','inputCanvas');


            var brushButton = _svg.append('g')
                    .attr('id', 'selectButton')
                    .append('rect')
                    .attr('width', '80px')
                    .attr('height', '15px')
                    .attr('x', 0).attr('y', 0).attr('rx', 5)
                    .style('fill', '#ccc')
                    .on('click', function () {
                        _observers.notify({
                            type: globals.signals.TOGGLEBRUSH
                        })
                    });
            var brushButtonText = d3.select(elem).select('#selectButton').append('text')
                    .attr("x", 3)
                    .attr("y", 12)
                    .text('Select nodes')
                    .attr("font-family", "sans-serif")
                    .attr("font-size", "12px")
                    .attr('cursor', 'pointer')
                    .on('click', function () {
                        _observers.notify({
                            type: globals.signals.TOGGLEBRUSH
                        })
                    });

            var colorButton = _svg.append('g')
                    .attr('id', 'colorButton')
                    .append('rect')
                    .attr('width', '90px')
                    .attr('height', '15px')
                    .attr('x', 90).attr('y', 0).attr('rx', 5)
                    .style('fill', '#ccc');

            var colorButtonText = d3.select(elem).select('#colorButton').append('text')
                    .attr("x", 93)
                    .attr("y", 12)
                    .text(function(){
                        return `Colors: ${model.data["colors"][model.state["colorScheme"]]}`
                    })
                    .attr("font-family", "sans-serif")
                    .attr("font-size", "12px")
                    .attr('cursor', 'pointer')
                    .on('click', function () {
                        _observers.notify({
                            type: globals.signals.COLORCLICK
                        })
                    });

            var unifyLegends = _svg.append('g')
                    .attr('id', 'unifyLegends')
                    .append('rect')
                    .attr('width', '100px')
                    .attr('height', '15px')
                    .attr('x', 190)
                    .attr('y', 0)
                    .attr('rx', 5)
                    .style('fill', '#ccc');
            var legendText = d3.select(elem).select('#unifyLegends').append('text')
                    .attr("x", 195)
                    .attr("y", 12)
                    .text(function(){ return `Legends: ${model.data["legends"][model.state["legend"]]}`})
                    .attr("font-family", "sans-serif")
                    .attr("font-size", "12px")
                    .attr('cursor', 'pointer')
                    .on('click', function () {
                        _observers.notify({
                            type: globals.signals.LEGENDCLICK
                        });
                    });
            
            _svg.attr('height', '15px').attr('width', width);


           // ----------------------------------------------
            // Define and set d3 callbacks for changes
            // ----------------------------------------------
            var brush = d3.brush()
                    .extent([[0, 0], [2 * width, 2 * (height + globals.layout.margin.top + globals.layout.margin.bottom)]])
                    .on('brush', function(){
                        _observers.notify({
                            type: globals.signals.BRUSH,
                            selection: d3.event.selection,
                            end: false
                        })
                    })
                    .on('end', function(){
                        _observers.notify({
                            type: globals.signals.BRUSH,
                            selection: d3.event.selection,
                            end: true
                        })
                    });

            const gBrush = d3.select("#mainG").append('g')
                    .attr('class', 'brush')
                    .call(brush);
            
                
            //When metricSelect is changed (metric_col)
            d3.select(element).select('#metricSelect')
            .on('change', function () {
                _observers.notify({
                    type: globals.signals.METRICCHANGE,
                    newMetric: this.value
                })
            });

            return{
                register: function(s){
                    _observers.add(s);
                },
                render: function(){
                    /**
                     * Core call for drawing menu related screen elements
                     */

                    selectedMetric = model.state["selectedMetric"];
                    brushOn = model.state["brushOn"];
                    curColor = model.state["colorScheme"];
                    colors = model.data["colors"];
                    curLegend = model.state["legend"];
                    legends = model.data["legends"];

                    //Remove brush and reset if active
                    d3.selectAll('.brush').remove();

                    //updates
                    brushButton.style("fill", function(){ 
                        if(brushOn > 0){
                            return "black";
                        }
                        else{
                            return "#ccc";
                        }
                    })
                    .attr('cursor', 'pointer');

                    brushButtonText.style("fill", function(){
                        if(brushOn > 0){
                            return "white";
                        }
                        else{
                            return "black";
                        }
                    })
                    .attr('cursor', 'pointer');


                    //add brush if there should be one
                    if(brushOn > 0){
                        d3.select("#mainG").append('g')
                            .attr('class', 'brush')
                            .call(brush);
                    } 

                    colorButtonText
                    .text(function(){
                        return `Colors: ${colors[curColor]}`;
                    })

                    legendText
                    .text(function(){
                        return `Legends: ${legends[curLegend]}`;
                    })
                }
            }
        }

        var createChartView = function(elem, model){
            let _observers = makeSignaller();
            var _colorManager = makeColorManager(model);
            var forestData = model.data["forestData"];
            var width = elem.clientWidth - globals.layout.margin.right - globals.layout.margin.left;
            var height = globals.layout.margin.top + globals.layout.margin.bottom;
            var _margin = globals.layout.margin;
            var _nodeRadius = 30;
            var treeLayoutHeights = [];


            var svg = d3.select(elem)
                        .append('svg')
                        .attr("class", "canvas")
                        .attr("width", width)
                        .attr("height", height);

            //layout variables            
            var spreadFactor = 0;
            var legendOffset = 0;
            var maxHeight = 0;
            var chartOffset = 0;
            var treeOffset = 0;
            var minmax = [];


            
            function diagonal(s, d) {
                /**
                 * Creates a curved diagonal path from parent to child nodes
                 * 
                 * @param {Object} s - parent node
                 * @param {Object} d - child node
                 * 
                 */

                let path = `M ${s.y} ${s.x}
                C ${(s.y + d.y) / 2} ${s.x},
                ${(s.y + d.y) / 2} ${d.x},
                ${d.y} ${d.x}`

                return path
            }

            function _getMinxMaxxFromTree(root){
                /**
                 * Get the minimum x value and maximum x value from a tree layout
                 * Used for calculating canvas offsets before drawing
                 * 
                 * @param {Object} root - The root node of the working tree
                 */

                var obj = {}
                var min = Infinity;
                var max = -Infinity;
                root.descendants().forEach(function(d){
                    max = Math.max(d.x, max);
                    min = Math.min(d.x, min);
                })

                obj.min = min;
                obj.max = max;

                return obj;
            }

            function _getHeightFromTree(root){
                /**
                 * Get the vertical space required to draw the tree
                 * by subtracting the min x value from the maximum
                 * 
                 * @param {Object} root - The root node of the working tree
                 */
                let minmax = _getMinxMaxxFromTree(root);
                let min = minmax["min"];
                let max = minmax["max"];

                return max - min;
            }

            // --------------------------------------------------------------
            // Initialize layout before first render
            // --------------------------------------------------------------

            var mainG = svg.append("g")
                            .attr('id', "mainG")
                            .attr("transform", "translate(" + globals.layout.margin.left + "," + 0 + ")");

            var tree = d3.tree().nodeSize([_nodeRadius, _nodeRadius]);

            // Find the tallest tree for layout purposes (used to set a uniform spreadFactor)
            for (var treeIndex = 0; treeIndex < forestData.length; treeIndex++) {
                var currentTreeData = forestData[treeIndex];
                var currentRoot = d3.hierarchy(currentTreeData, d => d.children);

                currentRoot.x0 = height;
                currentRoot.y0 = _margin.left;

                var currentTree = tree(currentRoot);

                if (currentTree.height > maxHeight) {
                    maxHeight = currentTree.height;
                }

                model.addTree(currentTree);

                treeLayoutHeights.push(_getHeightFromTree(currentRoot));
                minmax.push(_getMinxMaxxFromTree(currentRoot))
            }

            //layout variables            
            spreadFactor = width / (maxHeight + 1);

            // Add a group and tree for each tree in the current forest
            for (var treeIndex = 0; treeIndex < forestData.length; treeIndex++) {
                model.updateforestStats(treeIndex);
                
                var currentTree = model.getTree(treeIndex);
                var newg = mainG.append("g")
                        .attr('class', 'group-' + treeIndex + ' subchart')
                        .attr('tree_id', treeIndex)
                        .attr("transform", "translate(" + _margin.left + "," + chartOffset + ")");

                const legGroup = newg
                    .append('g')
                    .attr('class', 'legend-grp-' + treeIndex)
                    .attr('transform', 'translate(0, 0)');

                const legendGroups = legGroup.selectAll("g")
                        .data([0, 1, 2, 3, 4, 5])
                        .enter()
                        .append('g')
                        .attr('class', 'legend legend' + treeIndex)
                        .attr('transform', (d, i) => {
                            const y = 18 * i;
                            return "translate(-20, " + y + ")";
                        });
                const legendRects = legendGroups.append('rect')
                        .attr('class', 'legend legend' + treeIndex)
                        .attr('x', 0)
                        .attr('y', 0)
                        .attr('height', 15)
                        .attr('width', 10)
                        .style('stroke', 'black');
                const legendText = legendGroups.append('text')
                        .attr('class', 'legend legend' + treeIndex)
                        .attr('x', 12)
                        .attr('y', 13)
                        .text("0.0 - 0.0")
                        .style('font-family', 'monospace')
                        .style('font-size', '12px');

                legendOffset = legGroup.node().getBBox().height;


                //make an invisible rectangle for zooming on
                newg.append('rect')
                    .attr('height', treeLayoutHeights[treeIndex])
                    .attr('width', width)
                    .attr('fill', 'rgba(0,0,0,0)');

                //put tree itself into a group
                newg.append('g')
                    .attr('class', 'chart')
                    .attr('chart-id', treeIndex)
                    .attr('height', globals.treeHeight)
                    .attr('width', width)
                    .attr('fill', 'rgba(0,0,0,0)');

                //Create d3 zoom element and affix to each tree individually
                var zoom = d3.zoom().on("zoom", function (){
                    let zoomObj = d3.select(this).selectAll(".chart");

                    zoomObj.attr("transform", d3.event.transform);

                    //update for scale view
                    _observers.notify({
                        type: globals.signals.ZOOM,
                        index: zoomObj.attr("chart-id"),
                        transformation: zoomObj.node().getCTM()
                    })
                });

                newg.call(zoom)
                    .on("dblclick.zoom", null);
                
                //X value where tree should start being drawn
                treeOffset = 0 + legendOffset + _margin.top;

                //Initialize nodes with x/y data based on their current location
                model.updateNodes(treeIndex,
                    function(n){
                        // Normalize for fixed-depth.
                        n.forEach(function (d) {
                            d.x = d.x + treeOffset - minmax[treeIndex]["min"];
                            d.y = (d.depth * spreadFactor);

                            d.x0 = d.x;
                            d.y0 = d.y;

                            // Store the overall position based on group
                            d.xMainG = d.x + chartOffset;
                            d.yMainG = d.y + _margin.left;

                            d.xMainG0 = d.xMainG;
                            d.yMainG0 = d.yMainG;
                        });
                    }
                );

                newg.style("display", "inline-block");
            } //end for-loop "add tree"



            return{
                register: function(s){
                    _observers.add(s);
                },
                render: function(){
                    /**
                     * Core render function for the chart portion of the view, including legends
                     * Called from the model with observers.notify
                     * 
                     */

                    chartOffset = _margin.top;
                    height = _margin.top + _margin.bottom;

                    //render for any number of trees
                    for(var treeIndex = 0; treeIndex < model.data["numberOfTrees"]; treeIndex++){

                        let lastClicked = model.state["lastClicked"];

                        var source = d3.hierarchy(model.data["forestData"][treeIndex], d => d.children);
                        var selectedMetric = model.state["selectedMetric"];
                        var nodes = model.getNodesFromMap(treeIndex);
                        var links = model.getLinksFromMap(treeIndex);
                        var chart = svg.selectAll('.group-' + treeIndex);
                        var tree = chart.selectAll('.chart');

                        // ---------------------------------------------
                        // ENTER 
                        // ---------------------------------------------
                        // Update the nodes…
                        var i = 0;
                        var node = tree.selectAll("g.node")
                                .data(nodes, function (d) {
                                    return d.id || (d.id = ++i);
                                });
                        
                        // Enter any new nodes at the parent's previous position.
                        var nodeEnter = node.enter().append('g')
                                .attr('class', 'node')
                                .attr("transform", () => {return "translate(" + lastClicked.y + "," + lastClicked.x + ")"})
                                .on("click", function(d){
                                    _observers.notify({
                                        type: globals.signals.CLICK,
                                        node: d
                                    })
                                })
                                .on('dblclick', function (d) {
                                    _observers.notify({
                                        type: globals.signals.DBLCLICK,
                                        node: d,
                                        tree: treeIndex
                                    })
                                });
            
                        nodeEnter.append("circle")
                                .attr('class', 'circleNode')
                                .attr("r", 1e-6)
                                .style("fill", function (d) {
                                    if(model.state["legend"] == globals.UNIFIED){
                                        return _colorManager.calcColorScale(d.data.metrics[selectedMetric], -1);
                                    }
                                    return _colorManager.calcColorScale(d.data.metrics[selectedMetric], treeIndex);
                                })
                                .style('stroke-width', '1px')
                                .style('stroke', 'black');
            
                        //Append text to nodes
                        nodeEnter.append("text")
                        .attr("x", function (d) {
                            return d.children || model.state['collapsedNodes'].includes(d) ? -13 : 13;
                        })
                        .attr("dy", ".75em")
                        .attr("text-anchor", function (d) {
                            return d.children || model.state['collapsedNodes'].includes(d) ? "end" : "start";
                        })
                        .text(function (d) {
                            if(!d.children){
                                return d.data.name;
                            }
                            else if(d.children.length == 1){
                                return "";
                            }
                            else {
                                return d.data.name.slice(0,5) + "...";
                            }
                        })
                        .style("font", "12px monospace");



                        // links
                        var link = tree.selectAll("path.link")
                        .data(links, function (d) {
                            return d.id;
                        });
        
                        // Enter any new links at the parent's previous position.
                        var linkEnter = link.enter().insert("path", "g")
                                .attr("class", "link")
                                .attr("d", function (d) {
                                    var o = {x: nodes[0].x, y: nodes[0].y};
                                    return diagonal(o, o);
                                })
                                .attr('fill', 'none')
                                .attr('stroke', '#ccc')
                                .attr('stroke-width', '2px');

        
                        // ---------------------------------------------
                        // Updates 
                        // ---------------------------------------------
                        var nodeUpdate = nodeEnter.merge(node);
                        var linkUpdate = linkEnter.merge(link);
                
                        // Chart updates
                        chart
                        .transition()
                        .duration(globals.duration)
                        .attr("transform", function(){
                            if(model.state["activeTree"].includes(model.data["rootNodeNames"][treeIndex+1])){
                                return `translate(${_margin.left}, ${_margin.top})`;
                            } 
                            else {
                                return `translate(${_margin.left}, ${chartOffset})`;
                            }
                        })    
                        .style("display", function(){
                            if(model.state["activeTree"].includes("Show all trees")){
                                return "inline-block";
                            } 
                            else if(model.state["activeTree"].includes(model.data["rootNodeNames"][treeIndex+1])){
                                return "inline-block";
                            } 
                            else {
                                return "none";
                            }
                        });

                        //legend updates
                        chart.selectAll(".legend rect")
                            .transition()
                            .duration(globals.duration)
                            .attr('fill', function (d, i) {
                                return _colorManager.getColorLegend(treeIndex)[d];
                            })
                            .attr('stroke', 'black');

                        chart.selectAll('.legend text')
                            .transition()
                            .duration(globals.duration)
                            .text((d) => { return _colorManager.getLegendDomains(treeIndex)[6 - d - 1] + ' - ' + _colorManager.getLegendDomains(treeIndex)[6 - d]; });


                        // Transition links to their new position.
                        linkUpdate.transition()
                                .duration(globals.duration)
                                .attr("d", function (d) {
                                    return diagonal(d, d.parent);
                                });

            
                        // Transition nodes to their new position.
                        nodeUpdate.transition()
                                .duration(globals.duration)
                                .attr("transform", function (d) {
                                    return `translate(${d.y}, ${d.x})`;
                                });

                        nodeUpdate.select('circle.circleNode')
                                .attr("r", 5)
                                .style('stroke', function(d){
                                    if (model.state['collapsedNodes'].includes(d)){
                                        return "#89c3e0";
                                    }
                                    else{
                                        return 'black';
                                    }
                                })
                                .style("stroke-dasharray", function (d) {
                                    return model.state['collapsedNodes'].includes(d) ? '4' : '0';
                                }) //lightblue
                                .style('stroke-width', function(d){
                                    if (model.state['collapsedNodes'].includes(d)){
                                        return '6px';
                                    } 
                                    else if (model.state['selectedNodes'].includes(d)){
                                        return '4px';
                                    } 
                                    else {
                                        return '1px';
                                    }
                                })
                                .attr('cursor', 'pointer')
                                .transition()
                                .duration(globals.duration)
                                .style('fill', function (d) {
                                    if(model.state["legend"] == globals.UNIFIED){
                                        return _colorManager.calcColorScale(d.data.metrics[selectedMetric], -1);
                                    }
                                    return _colorManager.calcColorScale(d.data.metrics[selectedMetric], treeIndex);

                                })

                        nodeUpdate.select('text')
                                .attr("x", function (d) {
                                    return d.children || model.state['collapsedNodes'].includes(d) ? -13 : 13;
                                })
                                .attr("dy", ".75em")
                                .attr("text-anchor", function (d) {
                                    return d.children || model.state['collapsedNodes'].includes(d) ? "end" : "start";
                                })
                                .text(function (d) {
                                    if(!d.children){
                                        return d.data.name;
                                    }
                                    else if(d.children.length == 1){
                                        return "";
                                    }
                                    else {
                                        return d.data.name.slice(0,5) + "...";
                                    }
                                })
                                .style("font", "12px monospace")
                                .attr("fill", "black");


                                
                        // ---------------------------------------------
                        // Exit
                        // ---------------------------------------------
                        // Transition exiting nodes to the parent's new position.
                        var nodeExit = node.exit().transition()
                                .duration(globals.duration)
                                .attr("transform", function (d) {
                                    return "translate(" + lastClicked.y + "," + lastClicked.x + ")";
                                })
                                .remove();
            
                        nodeExit.select("circle")
                                .attr("r", 1e-6);
            
                        nodeExit.select("text")
                                .style("fill-opacity", 1);
            
                        // Transition exiting links to the parent's new position.
                        var linkExit = link.exit().transition()
                                .duration(globals.duration)
                                .attr("d", function (d) {
                                    var o = {x: source.x, y: source.y};
                                    return diagonal(o, o);
                                })
                                .remove();

                        chartOffset = treeLayoutHeights[treeIndex] + treeOffset + _margin.top;
                        height += chartOffset;
                    }                    

                    svg.attr("height", height);
                }
            }
            
        }

        var createTooltipView = function(elem, model){
            /**
             * Class that instantiates the view for the tooltip that appears with selected nodes.
             * 
             * @param {DOM Element} elem - The current cell of the calling Jupyter notebook
             * @param {Model} model - The model object containg data for the view
             */
            var _observers = makeSignaller();
            var _tooltip = d3.select(elem).append("div")
                    .attr('id', 'tooltip')
                    .style('position', 'absolute')
                    .style('top', '5px')
                    .style('right', '15px')
                    .style('padding', '5px')
                    .style('border-radius', '5px')
                    .style('background', '#ccc')
                    .style('color', 'black')
                    .style('font-size', '14px')
                    .style('font-family', 'monospace')
                    .html('<p>Click a node or "Select nodes" to see more info</p>');

            return {
                register: function(s){
                    _observers.add(s);
                },
                render: function(){
                    _tooltip.html(model.data["tipText"]);
                }
            }
        }

        // ---------------------------------------------
        // Main driver area 
        // ---------------------------------------------
        
        //model
        var model = createModel();
        //controller
        var controller = createController(model);
        //views
        var menu = createMenuView(element, model);
        var tooltip = createTooltipView(element, model);
        var chart = createChartView(element, model);
        
        //render all views one time
        menu.render();
        tooltip.render();
        chart.render();
        
        //register signallers with each class
        // tooltip is not interactive so 
        // it does not need a signaller yet
        menu.register(controller.dispatch);
        chart.register(controller.dispatch);

        model.register(menu.render);
        model.register(chart.render);
        model.register(tooltip.render);

    });

})(element);
