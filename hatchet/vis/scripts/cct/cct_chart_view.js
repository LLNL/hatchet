import { d3, globals } from "./cct_globals";
import ColorManager from "./cct_color_manager";
import View from "../utils/view";

class Legend extends View{
    constructor(elem, model, encoding_type, tree_index, cm, nodeScale){
        super(elem, model);
        this._colorManager = cm;
        this._nodeScale = nodeScale;
        this.metricColumns = model.forest.metricColumns;
        this.attributeColumns = model.forest.attributeColumns;
        this.tree_index = tree_index;
        this.secondaryMinMax = this.model.forest.forestMinMax;

        this.type = encoding_type;
        this.agg = false;

        this.leg_grp = elem
                    .append('g')
                    .attr('class', 'legend-grp');
        
        this.quantNodeScale = d3.scaleQuantize().range([0,1,2,3,4,5]).domain([this.secondaryMinMax[this.model.state.secondaryMetric].min, this.secondaryMinMax[this.model.state.secondaryMetric].max]);

        this.preRender();

    }

    setAgg(){
        this.agg = true;
    }

    offset(x){
        this.leg_grp.attr('transform', `translate(${x}, 0)`);
    }

    getLegendWidth(){
        return this.leg_grp.node().getBBox().width;
    }

    getLegendHeight(){
        return this.leg_grp.node().getBBox().height;
    }

    preRender(){

        this.leg_grp.append('text')
                    .text(()=>{
                        if(this.type == 'color'){
                            return `Legend for metric: ${this.model.state.primaryMetric}`;
                        }
                        else if(this.type == 'radius'){
                            return `Legend for metric: ${this.model.state.secondaryMetric}`;
                        }
                    })
                    .attr('class', 'legend-title')
                    .attr('x', '-2em')
                    .attr('y', '-1em')
                    .attr('font-family', 'sans-serif')
                    .attr('font-size', '14px');

        
        const legendGroups = this.leg_grp.selectAll("g")
                .data([0,1,2,3,4,5])
                .enter()
                .append('g')
                .attr('class', 'legend-lines')
                .attr('transform', (_,i) => {
                    if(this.type == 'color'){
                        const y = 18 * i;
                        return "translate(-20, " + y + ")";
                    }
                    else if(this.type == 'radius'){
                        return `translate(-20, ${i*(this._nodeScale(this.quantNodeScale.invertExtent(5)[0]+1)+13)})`;
                    }
                });

        //legend rectangles & text
        if(this.type == 'color'){
            legendGroups.append('rect')
                    .attr('class', 'legend-samples')
                    .attr('x', 0)
                    .attr('y', 0)
                    .attr('height', 15)
                    .attr('width', 10)
                    .style('stroke', 'black');

            legendGroups.append('text')
                    .attr('class', 'legend-ranges')
                    .attr('x', 12)
                    .attr('y', 13)
                    .text("0.0 - 0.0")
                    .style('font-family', 'monospace')
                    .style('font-size', '12px');
        }
        if(this.type == 'radius'){
            legendGroups.append('circle')
                    .attr('class', 'legend-samples')
                    .attr('cx', 0)
                    .attr('cy', (_,i)=>{
                        return (this._nodeScale(this.quantNodeScale.invertExtent(5)[0]+1)/2 + 3);
                    })
                    .attr('r', (_,i)=>{
                        return this._nodeScale(this.quantNodeScale.invertExtent(5-i)[0]+1);
                    })
                    .style('stroke', 'black')
                    .style('fill', 'white');

            legendGroups.append('text')
                    .attr('class', 'legend-ranges')
                    .attr('x', (_,i)=>{
                        return this._nodeScale(this.quantNodeScale.invertExtent(5)[0]+1)+5
                    }) 
                    .attr('y', 13)
                    .text("0.0 - 0.0")
                    .style('font-family', 'monospace')
                    .style('font-size', '12px');
        }
        this.legendOffset = this.leg_grp.node().getBBox().height;

    }

    render(){
        this.quantNodeScale.domain([this.secondaryMinMax[this.model.state.secondaryMetric].min, this.secondaryMinMax[this.model.state.secondaryMetric].max]);
        let leg_dom = this._colorManager.getLegendDomains(this.tree_index);

        
        this.leg_grp.selectAll(".legend-title")
            .text(()=>{
                if(this.type == 'color'){
                    return `Legend for metric: ${this.model.state.primaryMetric}`;
                }
                else if(this.type = 'radius'){
                    return `Legend for metric: ${this.model.state.secondaryMetric}`;
                }
            });

        this.leg_grp.selectAll(".legend-samples")
            .transition()
            .duration(globals.duration)
            .attr('fill', (d) => {
                if(this.type == "color"){
                    return this._colorManager.getColorLegend(this.tree_index)[5-d];
                }
                return 'white';
            })
            .attr('stroke', 'black');

        this.leg_grp.selectAll('.legend-ranges')
            .transition()
            .duration(globals.duration)
            .text((_, i) => {
                if(this.type == "color"){

                    if (this.metricColumns.includes(this.model.state["primaryMetric"])) {
                        return leg_dom[5 - i][0].toFixed(2) + ' - ' + leg_dom[5 - i][1].toFixed(2);
                    } 
                    else if (this.attributeColumns.includes(this.model.state["primaryMetric"])) {
                        return leg_dom[i];
                    }
                }
                else if(this.type == "radius"){
                    let range = this.quantNodeScale.invertExtent(5-i);
                    return `${range[0].toFixed(2)} - ${range[1].toFixed(2)}`;
                } 
            });

    }
}


class ChartView extends View{

    constructor(elem, model){
        super(elem, model);

        //layout variables
        this._margin = globals.layout.margin;     
        this._width = element.clientWidth - this._margin.right - this._margin.left;
        this._height = this._margin.top + this._margin.bottom;
        this._maxNodeRadius = 12;
        this._treeLayoutHeights = [];
        this.legendOffset = 0;
        this.chartOffset = this._margin.top;
        this.treeOffset = 0;
        this._minmax = [];

        this.svg = d3.select(elem)
                    .append('svg')
                    .attr("class", "canvas")
                    .attr("width", this._width)
                    .attr("height", this._height);

        const fMaxHeight = model.forest.maxHeight;
        const secondaryMinMax = model.forest.forestMinMax[model.state.secondaryMetric];

        //scales
        this._treeCanvasHeightScale = d3.scaleQuantize().range([250, 1000, 1250, 1500]).domain([1, 300]);
        this._treeDepthScale = d3.scaleLinear().range([0, element.offsetWidth-200]).domain([0, fMaxHeight])
        this._nodeScale = d3.scaleLinear().range([4, this._maxNodeRadius]).domain([secondaryMinMax.min, secondaryMinMax.max]);
        this._barScale = d3.scaleLinear().range([5, 25]).domain([secondaryMinMax.min, secondaryMinMax.max]);

        //view specific data stores
        this.nodes = [];
        this.surrogates = [];
        this.aggregates = [];
        this.links = [];
        this.metricColumns = model.forest.metricColumns;
        this.attributeColumns = model.forest.attributeColumns;

        this.primary_legends = [];
        this.secondary_legends = [];
        this.color_managers = [];

        this._preRender();
    }


    diagonal(s, d, ti) {
        /**
         * Creates a curved diagonal path from parent to child nodes
         * 
         * @param {Object} s - parent node
         * @param {Object} d - child node
         * 
         */
        var dy = this._treeDepthScale(d.depth);
        var sy = this._treeDepthScale(s.depth);
        var sx = this._getLocalNodeX(s.x, ti);
        var dx = this._getLocalNodeX(d.x, ti);
        let path = `M ${sy} ${sx}
        C ${(sy + dy) / 2} ${sx},
        ${(sy + dy) / 2} ${dx},
        ${dy} ${dx}`

        return path
    }

    _getLocalNodeX(x, ti){
        /**
         * Returns the local node x offset based on the current
         * tree layout.
         * 
         * @param {float} x - X offset of a node from d3.tree
         * @param {Number} ti - The current tree index
         */
        return x + this.treeOffset - this._minmax[ti].min;
    }

    _getMinxMaxxFromTree(root){
        /**
         * Get the minimum x value and maximum x value from a tree layout
         * Used for calculating canvas offsets before drawing
         * 
         * @param {Object} root - The root node of the working tree
         */

        var obj = {}
        var min = Infinity;
        var max = -Infinity;
        root.descendants().forEach((d) => {
            max = Math.max(d.x, max);
            min = Math.min(d.x, min);
        })

        obj.min = min;
        obj.max = max;

        return obj;
    }

    _getHeightFromTree(root){
        /**
         * Get the vertical space required to draw the tree
         * by subtracting the min x value from the maximum
         * 
         * @param {Object} root - The root node of the working tree
         */
        let minmax = this._getMinxMaxxFromTree(root);
        let min = minmax["min"];
        let max = minmax["max"];

        return max - min;
    }
    
    _getSelectedNodes(selection){
        /**
         * Function which calculates the collison of which nodes were brushed
         * 
         * @param {Array} selection - A 2d array containing the svg coordinates of the top left and bottom right
         *  points of a brushed bounding box
         */
        let brushedNodes = [];
        if (selection){
            for(var i = 0; i < this.model.forest.numberOfTrees; i++){
                this.nodes[i].forEach((d) => {
                    if(selection[0][0] <= d.yMainG && selection[1][0] >= d.yMainG 
                        && selection[0][1] <= d.xMainG && selection[1][1] >= d.xMainG){
                        brushedNodes.push(d);
                    }
                })
            }
        }

        return brushedNodes;

    }

    _calcNodePositions(nodes, treeIndex){
        /**
         * Calculates the local and gloabal node positions for each tree in
         *  our forest.
         * 
         * @param {Array} nodes - An array of all nodes in a tree
         * @param {Number} treeIndex - An integer of the current tree index
         */
        nodes.forEach(
            (d) => {
                    d.x0 = this._getLocalNodeX(d.x, treeIndex);
                    d.y0 = this._treeDepthScale(d.depth);
                
                    // Store the overall position based on group
                    d.xMainG = d.x0 + this.chartOffset;
                    d.yMainG = d.y0 + this._margin.left;
            }
        );
    }

    _preRender(){
        //For calls which need the context of
        // the d3 callback and class
        const self = this;

        var mainG = this.svg.append("g")
            .attr('id', "mainG")
            .attr("transform", "translate(" + globals.layout.margin.left + "," + globals.layout.margin.top + ")");
            
            // .nodeSize([this._maxNodeRadius, this._maxNodeRadius]);
        
        
        var zoom = d3.zoom()
            .on("zoom", function (){
                    let zoomObj = d3.select(this).selectAll(".chart");
                    zoomObj.attr("transform", d3.event.transform);
                })
                .on("end", function () {
                    let zoomObj = d3.select(this).selectAll(".chart");
                    let index = zoomObj.attr("chart-id");
                    let transformation = zoomObj.node().getCTM();

                    self.nodes[index].forEach((d) =>  {
                        /**
                         * This function gets the absolute location for each point based on the relative
                         * locations of the points based on transformations
                         * the margins were being added into the .e and .f values so they have to be subtracted
                         * Adapted from: https://stackoverflow.com/questions/18554224/getting-screen-positions-of-d3-nodes-after-transform
                         * 
                         */
                        
                        d.yMainG = transformation.e + d.y0*transformation.d + d.x0*transformation.c - globals.layout.margin.left;
                        d.xMainG = transformation.f + d.y0*transformation.b + d.x0*transformation.a - globals.layout.margin.top;
                    });
                });


        // Add a group and tree for each forestData[i]
        for (var treeIndex = 0; treeIndex < this.model.forest.numberOfTrees; treeIndex++) {
            let tree = d3.tree().size([this._treeCanvasHeightScale(this.model.forest.getCurrentTree(treeIndex).size), this._width - this._margin.left - 200]);
            let currentRoot = tree(this.model.forest.getCurrentTree(treeIndex));
            let currentLayoutHeight = this._getHeightFromTree(currentRoot);
            let currentMinMax = this._getMinxMaxxFromTree(currentRoot);
            
            var newg = mainG.append("g")
                    .attr('class', 'group-' + treeIndex + ' subchart')
                    .attr('tree_id', treeIndex)
                    .attr("transform", "translate(" + this._margin.left + "," + this.chartOffset + ")");

            let cm = new ColorManager(this.model, treeIndex);

            let primary_legend = new Legend(newg, this.model, 'color', treeIndex, cm, this._nodeScale);
            let secondary_legend = new Legend(newg, this.model, 'radius', treeIndex, cm, this._nodeScale);

            secondary_legend.offset(primary_legend.getLegendWidth()+20);

            this.color_managers.push(cm);
            this.primary_legends.push(primary_legend);
            this.secondary_legends.push(secondary_legend);

            this.legendOffset = this.primary_legends[treeIndex].getLegendHeight();

            //make an invisible rectangle for zooming on
            newg.append('rect')
                .attr('height', this._treeLayoutHeights[treeIndex])
                .attr('width', this._width)
                .attr('fill', 'rgba(0,0,0,0)');

            //put tree itself into a group
            newg.append('g')
                .attr('class', 'chart')
                .attr('chart-id', treeIndex)
                .attr('height', globals.treeHeight)
                .attr('width', this._width)
                .attr('fill', 'rgba(0,0,0,0)');

            this.treeOffset = 0 + this.legendOffset + this._margin.top;

            newg.style("display", "inline-block");

            //store node and link layout data for use later
            var treeLayout = tree(this.model.forest.getCurrentTree(treeIndex));
            this.nodes.push(treeLayout.descendants());

            this.surrogates.push([]);
            this.aggregates.push([]);
            this.links.push(treeLayout.descendants().slice(1));
            
            //storage
            this._treeLayoutHeights.push(currentLayoutHeight);
            this._minmax.push(currentMinMax);

            //updates
            // put this on the immutable tree
            this._calcNodePositions(this.nodes[treeIndex], treeIndex);

            this.chartOffset = this._treeLayoutHeights[treeIndex] + this.treeOffset + this._margin.top;
            this._height += this.chartOffset;


            newg.call(zoom)
                .on("dblclick.zoom", null);

        }
        
        //Update the height
        this.svg.attr("height", this._height);

        //setup Interactions
        this.brush = d3.brush()
        .extent([[0, 0], [2 * this._width, 2 * (this._height + globals.layout.margin.top + globals.layout.margin.bottom)]])
        .on('brush', function(){
        })
        .on('end', () => {
            var selection = this._getSelectedNodes(d3.event.selection);
            this.observers.notify({
                type: globals.signals.BRUSH,
                selection: selection
            })
        });
    }


    render(){
        /**
             * Core render function for the chart portion of the view, including legends
             * Called from the model with observers.notify
             * 
             */
        
        const self = this;
        this.chartOffset = this._margin.top;
        this._height = this._margin.top + this._margin.bottom;

        //update scales
        this._nodeScale.domain([0, this.model.forest.forestMinMax[this.model.state.secondaryMetric].max]);
        this._barScale.domain([this.model.forest.aggregateMinMax[this.model.state.secondaryMetric].min, this.model.forest.aggregateMinMax[this.model.state.secondaryMetric].max]);

        //add brush if there should be one
        if(this.model.state.brushOn > 0){
             this.svg.select("#mainG").append('g')
                 .attr('class', 'brush')
                 .call(this.brush);
        } 

        //render for any number of trees
        for(var treeIndex = 0; treeIndex < this.model.forest.numberOfTrees; treeIndex++){
            //retrieve new data from model
            var secondaryMetric = this.model.state.secondaryMetric;
            var source = this.model.forest.getCurrentTree(treeIndex);

            //will need to optimize this redrawing
            // by cacheing tree between calls
            if(this.model.state.hierarchyUpdated == true){
                let tree = d3.tree().size([this._treeCanvasHeightScale(this.model.forest.getCurrentTree(treeIndex).size), this._width - this._margin.left - 200]);
                var treeLayout = tree(source);
                this.nodes[treeIndex] = treeLayout.descendants().filter(d=>{return !d.dummy});
                this.surrogates[treeIndex] = treeLayout.descendants().filter(d=>{return (d.dummy && !d.aggregate)});
                this.aggregates[treeIndex] = treeLayout.descendants().filter(d=>{return d.aggregate});
                this.links[treeIndex] = treeLayout.descendants().slice(1);
                
                this._calcNodePositions(this.nodes[treeIndex], treeIndex);

                //recalculate layouts
                this._treeLayoutHeights[treeIndex] = this._getHeightFromTree(treeLayout);
                this._minmax[treeIndex] = this._getMinxMaxxFromTree(treeLayout);

                //only update after last tree
                if(treeIndex == this.model.forest.numberOfTrees - 1){
                    this.model.state.hierarchyUpdated = false;
                }

            }

            
            var chart = this.svg.selectAll('.group-' + treeIndex);
            var treeGroup = chart.selectAll('.chart');

            if(this.model.state.resetView == true){
                /**
                 * BUG - D3 TRANSFORM EVENET DOES NOT UPDATE
                 */
                treeGroup.attr("transform", "");

                this.nodes[treeIndex].forEach(
                    (d) =>  {
                        // Store the overall position based on group
                        d.xMainG = d.x0 + this.chartOffset;
                        d.yMainG = d.y0 + this._margin.left;
                    }
                );

                //only update after last tree
                if(treeIndex == this.model.forest.numberOfTrees - 1){
                    this.model.state.resetView = false;
                }
            }

            // ---------------------------------------------
            // ENTER 
            // ---------------------------------------------
            var node = treeGroup.selectAll("g.node")
                    .data(this.nodes[treeIndex], (d) =>  {
                        return d.data.metrics._hatchet_nid || d.data.id;
                    });
            
            var dummyNodes = treeGroup.selectAll("g.fakeNode")
                .data(this.surrogates[treeIndex], (d) =>  {
                    return d.data.metrics._hatchet_nid || d.data.id;
                });

            var aggBars = treeGroup.selectAll("g.aggBar")
                .data(this.aggregates[treeIndex], (d) =>  {
                    return d.data.metrics._hatchet_nid || d.data.id;
                });
            
            // Enter any new nodes at the parent's previous position.
            var nodeEnter = node.enter().append('g')
                    .attr('class', 'node')
                    .attr("transform", (d) =>  {
                        if(!d.parent){
                            return "translate(0,0)"
                        }
                        return "translate(" + d.parent.y + "," + d.parent.x + ")";
                    })
                    .on("click", (d) => {
                        console.log(d);
                        this.observers.notify({
                            type: globals.signals.CLICK,
                            node: d
                        })
                    })
                    .on('dblclick', (d) =>  {
                        this.observers.notify({
                            type: globals.signals.DBLCLICK,
                            node: d,
                            tree: treeIndex
                        })
                    });


            var dNodeEnter = dummyNodes.enter().append('g')
                .attr('class', 'fakeNode')
                .on("click", (d) => {
                    this.observers.notify({
                        type: globals.signals.CLICK,
                        node: d
                    })
                })
                .on('dblclick', (d) =>  {
                    this.observers.notify({
                        type: globals.signals.DBLCLICK,
                        node: d
                    })
                });
            
            var aggNodeEnter = aggBars.enter().append('g')
                .attr('class', 'aggBar')
                .attr("transform", (d) =>  {
                    return `translate(${this._treeDepthScale(d.depth)}, ${this._getLocalNodeX(d.x, treeIndex)})`;
                })
                .on("click", (d) => {
                    this.observers.notify({
                        type: globals.signals.CLICK,
                        node: d
                    })
                })
                .on('dblclick', (d) =>  {
                    this.observers.notify({
                        type: globals.signals.DBLCLICK,
                        node: d
                    })
                });
            

            nodeEnter.append("circle")
                    .attr('class', 'circleNode')
                    .attr("r", 1e-6)
                    .style("fill", (d) => {
                        return this.color_managers[treeIndex].calcColorScale(d.data);
                    })
                    .style('stroke-width', '1px')
                    .style('stroke', 'black');

            dNodeEnter.append("path")
                    .attr('class', 'dummyNode')
                    .attr("d", "M 6 2 C 6 2 5 2 5 3 S 6 4 6 4 S 7 4 7 3 S 6 2 6 2 Z M 6 3 S 6 3 6 3 Z M 8 0 C 8 0 7 0 7 1 C 7 1 7 2 8 2 C 8 2 9 2 9 1 C 9 0 8 0 8 0 M 9 5 C 9 4 8 4 8 4 S 7 4 7 5 S 8 6 8 6 S 9 6 9 5")
                    .attr("fill", "rgba(0,0,0, .4)")
                    .style("stroke-width", ".5px")
                    .style("stroke", "rgba(100,100,100)");
            
            aggNodeEnter.append("rect")
                    .attr('class', 'bar')
                    .attr('height', (d) => {return this._barScale(d.data.aggregateMetrics[secondaryMetric]);})
                    .attr('width', 20)
                    .attr("fill", "rgba(0,0,0)")
                    .style("stroke-width", ".5px")
                    .style("stroke", "rgba(100,100,100)");

                    

            // commenting out text for now
            nodeEnter.append("text")
                    .attr("x", (d) => {
                        return d.children || this.model.state['collapsedNodes'].includes(d) ? -13 : 13;
                    })
                    .attr("dy", ".75em")
                    .attr("text-anchor", (d) => {
                        return d.children || this.model.state['collapsedNodes'].includes(d) ? "end" : "start";
                    })
                    .text((d) => {
                        if(!d.children){
                            let n = d.data.name;
                            if (n.includes("<unknown file>")){
                                n = n.replace('<unknown file>', '');
                            }
                            return n;
                        }
                        else if(d.children.length == 1){
                            return "";
                        }
                        return "";
                    })
                    .style("font", "12px monospace")
                    .style('fill','rgba(0,0,0,.9)');

            dNodeEnter.append("text")
                .attr("x", function () {
                    return 30;
                })
                .attr("dy", "1em")
                .attr("text-anchor", function () {
                    return "start";
                })
                .text((d) =>  {
                    if (d.elided.length > 1){
                        return `Children of: ${d.parent.data.name}` ;
                    } 
                    else{
                        return `${d.data.name} Subtree`;
                    }
                })
                .style("font", "12px monospace")
                .style('fill','rgba(0,0,0,.9)');

            aggNodeEnter.append("text")
                .attr("x", function () {
                    return 25;
                })
                .attr("dy", "1em")
                .attr("text-anchor", function () {
                    return "start";
                })
                .text((d) =>  {
                    if (d.elided.length > 1){
                        let n = d.parent.data.name;
                        if (n.includes("<unknown file>")){
                            n = n.replace('<unknown file>', '');
                        }
                        return `Children of: ${n}` ;
                    } 
                    else{
                        let n = d.data.name;
                        if (n.includes("<unknown file>")){
                            n = n.replace('<unknown file>', '');
                        }
                        return `${n} Subtree`;
                    }
                })
                .style("font", "12px monospace")
                .style('fill','rgba(0,0,0,.9)');


            // links
            var link = treeGroup.selectAll("path.link")
            .data(this.links[treeIndex], (d) =>  {
                return d.data.metrics._hatchet_nid || d.data.id;
            });

            // Enter any new links at the parent's previous position.
            var linkEnter = link.enter().insert("path", "g")
                    .attr("class", "link")
                    .attr("d", (d) =>  {
                        return this.diagonal(d.parent, d.parent, treeIndex);
                    })
                    .attr('fill', 'none')
                    .attr('stroke', '#ccc')
                    .attr('stroke-width', '2px');


            // ---------------------------------------------
            // Updates 
            // ---------------------------------------------
            var nodeUpdate = nodeEnter.merge(node);
            var dNodeUpdate = dNodeEnter.merge(dummyNodes);
            var linkUpdate = linkEnter.merge(link);
            var aggNodeUpdate = aggNodeEnter.merge(aggBars);
            
            // Chart updates
            chart
                .transition()
                .duration(globals.duration)
                .attr("transform", () => {
                    if(this.model.state["activeTree"].includes(this.model.forest.rootNodeNames[treeIndex+1])){
                        return `translate(${this._margin.left}, ${this._margin.top})`;
                    } 
                    else {
                        return `translate(${this._margin.left}, ${this.chartOffset})`;
                    }
                })    
                .style("display", () => {
                    if(this.model.state["activeTree"].includes("Show all trees")){
                        return "inline-block";
                    } 
                    else if(this.model.state["activeTree"].includes(this.model.forest.rootNodeNames[treeIndex+1])){
                        return "inline-block";
                    } 
                    else {
                        return "none";
                    }
                });

            //legend updates
            this.primary_legends[treeIndex].render();
            this.secondary_legends[treeIndex].render();



            // Transition links to their new position.
            linkUpdate.transition()
                    .duration(globals.duration)
                    .attr("d", (d) => {
                        return this.diagonal(d, d.parent, treeIndex);
                    });

            // Transition normal nodes to their new position.
            nodeUpdate
                .transition()
                .duration(globals.duration)
                .attr("transform", (d) => {
                    return `translate(${this._treeDepthScale(d.depth)}, ${this._getLocalNodeX(d.x, treeIndex)})`;
                });
                    
            //update other characteristics of nodes
            nodeUpdate
                .select('circle.circleNode')
                .style('stroke', (d) => {
                    if (this.model.state['collapsedNodes'].includes(d)){
                        return "#89c3e0";
                    }
                    else{
                        return 'black';
                    }
                })
                .style("stroke-dasharray", (d) => {
                    return this.model.state['collapsedNodes'].includes(d) ? '4' : '0';
                }) //lightblue
                .style('stroke-width', (d) => {
                    if (this.model.state['collapsedNodes'].includes(d)){
                        return '6px';
                    } 
                    else if (this.model.state['selectedNodes'].some(n=>n.data.id == d.data.id)){
                        return '4px';
                    } 
                    else {
                        return '1px';
                    }
                })
                .attr('cursor', 'pointer')
                .transition()
                .duration(globals.duration)
                .attr("r", (d, i) => {
                    if (this.model.state['selectedNodes'].some(n=>n.data.id == d.data.id)){
                        return this._nodeScale(d.data.metrics[secondaryMetric]) + 2;
                    }
                    return this._nodeScale(d.data.metrics[secondaryMetric]);
                })
                .style('fill', (d) => {
                    return this.color_managers[treeIndex].calcColorScale(d.data);

                });
            
            nodeUpdate.select("text")
                .attr("x", (d) => {
                    return d.children || this.model.state['collapsedNodes'].includes(d) ? -13 : this._nodeScale(d.data.metrics[secondaryMetric]) + 5;
                })
                .attr("dy", ".5em")
                .attr("text-anchor", (d) => {
                    return d.children || this.model.state['collapsedNodes'].includes(d) ? "end" : "start";
                })
                .text((d) => {
                    if(!d.children || d.children.length == 0){
                    let n = d.data.name;
                        if (n.includes("<unknown file>")){
                            n = n.replace('<unknown file>', '');
                        }
                        return n;
                    }
                    return "";
                });
            
            dNodeUpdate
                .selectAll(".dummyNode")
                .attr("d", "M 6 2 C 6 2 5 2 5 3 S 6 4 6 4 S 7 4 7 3 S 6 2 6 2 Z M 6 3 S 6 3 6 3 Z M 8 0 C 8 0 7 0 7 1 C 7 1 7 2 8 2 C 8 2 9 2 9 1 C 9 0 8 0 8 0 M 9 5 C 9 4 8 4 8 4 S 7 4 7 5 S 8 6 8 6 S 9 6 9 5")
                .attr("fill", "rgba(180,180,180)")
                .style("stroke-width", ".5px")
                .style("stroke", "rgba(100,100,100)")
                .attr("transform", function () {
                    let scale = 3;
                    return `scale(${scale})`;
                });
            
            dNodeUpdate
                .transition()
                .duration(globals.duration)
                .attr("transform", function (d)  {
                        let h = d3.select(this).select('path').node().getBBox().height;
                        return `translate(${self._treeDepthScale(d.depth)-15}, ${self._getLocalNodeX(d.x, treeIndex) - (h+1)/2})`;
                });

            aggNodeUpdate
                .select('rect')
                .attr('height', (d) => {return  this._barScale(d.data.aggregateMetrics[secondaryMetric]);})
                .style('stroke-width', (d) => {
                    if (this.model.state['selectedNodes'].includes(d)){
                        return '3px';
                    } 
                    else {
                        return '1px';
                    }
                })
                .style('fill', (d) =>  {
                    return this.color_managers[treeIndex].calcColorScale(d.data);
                });

            aggNodeUpdate
                .transition()
                .duration(globals.duration)
                .attr("transform", function (d) {
                        let h = d3.select(this).select('rect').node().getBBox().height;
                        let w = d3.select(this).select('rect').node().getBBox().width;
                        return `translate(${self._treeDepthScale(d.depth)-w/3}, ${self._getLocalNodeX(d.x, treeIndex) - h/2})`;
                });
            
                    
            // ---------------------------------------------
            // Exit
            // ---------------------------------------------
            // Transition exiting nodes to the parent's new position.
            var nodeExit = node.exit().transition()
                .duration(globals.duration)
                .attr("transform", (d) =>  {
                    return "translate(" + this._treeDepthScale(d.parent.depth) + "," + this._getLocalNodeX(d.parent.x, treeIndex) + ")";
                })
                .remove();

            nodeExit.select("circle")
                .attr("r", 1e-6);

            nodeExit.select("text")
                .style("fill-opacity", 1)
                .remove();
            
            dummyNodes.exit()
                .remove();
            
            aggBars.exit()
                .remove();

            // Transition exiting links to the parent's new position.
        link.exit().transition()
                .duration(globals.duration)
                .attr("d", (d) =>  {
                    return this.diagonal(d.parent, d.parent, treeIndex);
                })
                .remove();
            
            // make canvas always fit tree height
            this.chartOffset = this._treeLayoutHeights[treeIndex] + this.treeOffset + this._margin.top;
            this._height += this.chartOffset;
        }                    

        this.svg.attr("height", this._height);
    }
}

export default ChartView;