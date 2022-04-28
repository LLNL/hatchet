import { d3, globals, getSigFigString, areaToRad } from "./cct_globals";
import ColorManager from "./cct_color_manager";
import View from "../utils/view";

class Legend extends View{
    /**
     * Handles the drawing and management of different types of legends.
     */
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
        /**
         * Offsets a legend by x pixels along the x axis
         */
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
                        return `translate(-20, ${i*(areaToRad(this._nodeScale(this.quantNodeScale.invertExtent(5)[0]+1))+13)})`;
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
                        return ( areaToRad(this._nodeScale(this.quantNodeScale.invertExtent(5)[0]+1))/2 + 3);
                    })
                    .attr('r', (_,i)=>{
                        return areaToRad(this._nodeScale(this.quantNodeScale.invertExtent(5-i)[0]+1));
                    })
                    .style('stroke', 'black')
                    .style('fill', 'white');

            legendGroups.append('text')
                    .attr('class', 'legend-ranges')
                    .attr('x', (_,i)=>{
                        return areaToRad(this._nodeScale(this.quantNodeScale.invertExtent(5)[0]+1))+5
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
                        return getSigFigString(leg_dom[5-i][0]) + ' - ' + getSigFigString(leg_dom[5-i][1]);
                    } 
                    else if (this.attributeColumns.includes(this.model.state["primaryMetric"])) {
                        return leg_dom[i];
                    }
                }
                else if(this.type == "radius"){
                    let range = this.quantNodeScale.invertExtent(5-i);
                    return `${getSigFigString(range[0])} - ${getSigFigString(range[1])}`;
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
        this._maxNodeArea = 144*Math.PI;
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
        this._treeCanvasHeightScale = d3.scaleQuantize().range([450, 1250, 1500, 1750]).domain([1, 300]);
        this._treeDepthScale = d3.scaleLinear().range([0, element.offsetWidth-200]).domain([0, fMaxHeight])
        this._nodeScale = d3.scaleLinear().range([16*Math.PI, this._maxNodeArea]).domain([secondaryMinMax.min, secondaryMinMax.max]);

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

        this.newDataFlag = 1;

        this._preRender();
    }


    checkCollison(box1, box2){
        /**
         * Collision checking algorithm.
         * Used on text bounding boxes for
         * mitigating text overlap in dense
         * node clusters.
         */
        if(box1.x < box2.x + box2.width &&
           box1.x + box1.width > box2.x &&
           box1.y < box2.y + box2.height &&
           box1.y + box1.height > box2.y){
               return true;
        }
        return false;
    }


    manageLabelCollisions(nodes){
        /**
         * Main label collision management algorithm.
         *  Orders all labels by y coordinate and only checks
         *  a small number of possible conflicts as defined
         *  by their proximity to the tested label.
         */

        if(!this.newDataFlag){
            return;
        }

        let self = this;

        let testBBs = [];
        //load bounding boxes 
        nodes.each(function(d){
            if(d.children != undefined && d.children.length > 0){
                return;
            }

            let currentBox = {};
            currentBox.y = d.xMainG;
            currentBox.x = d.yMainG;
            currentBox.height = this.getBBox().height;
            currentBox.width = this.getBBox().width;
            currentBox.dat = d;

            testBBs.push(currentBox);
        });

        testBBs.sort((bb1, bb2) => bb1.y - bb2.y);

        let currentBox = null;
        let compareBox = null;
        let curr_d = null;
        let nd = null;
        for(let i = 0; i < testBBs.length-1; i ++){
            currentBox = testBBs[i];
            let cmpndx = i+1;
            compareBox = testBBs[cmpndx];
            while(cmpndx < testBBs.length && compareBox.y <= currentBox.y + 20){
                    if(self.checkCollison(currentBox, compareBox)){
                         //collision resolution conditionals
                        let rmv = null;
                        curr_d = currentBox.dat;
                        nd = compareBox.dat;

                        delete curr_d.data.text;

                        //comparing nodes of different depths
                        if(curr_d.depth > nd.depth){
                            rmv = nd;
                        }
                        else if(curr_d.depth < nd.depth){
                            rmv = curr_d;
                        }
                        else{
                            //comparing siblings
                            if(nd.data.metrics[self.model.state.primaryMetric] > curr_d.data.metrics[self.model.state.primaryMetric]){
                                rmv = curr_d;
                            }
                            else{
                                rmv = nd;
                            }
                        }

                        rmv.data.text = false;
                    }
                cmpndx += 1;
                compareBox = testBBs[cmpndx]
            }
        }
           
        nodes.select("text")
            .text((d) => {
                if((d.data.text === undefined) && (!d.children || d.children.length == 0)){
                    let n = d.data.name;
                    if (n.includes("<unknown file>")){
                        n = n.replace('<unknown file>', '');
                    }
                    return n;
                }
                return "";
            })
            .attr("text-anchor", (d)=>{
                if(d.data.text !== undefined || d.children){
                    return "end"
                }
            })
            .attr("x", (d) => {
                return d.children || d.data.text !== undefined ||this.model.state['collapsedNodes'].includes(d) ? -13 : areaToRad(this._nodeScale(d.data.metrics[this.model.state.secondaryMetric])) + 5;
            });

        this.newDataFlag = 0;
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
        const secondaryMetric = this.model.state.secondaryMetric;

        var mainG = this.svg.append("g")
            .attr('id', "mainG")
            .attr("transform", "translate(" + globals.layout.margin.left + "," + globals.layout.margin.top + ")")        
            .on('click', ()=>{
                if(self.model.state.menu_active){
                    self.observers.notify({type: globals.signals.TOGGLEMENU});
                }
            });
        
        
        this.zoom = d3.zoom()
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
            let layout = d3.tree().nodeSize([this._maxNodeRadius+4, this._maxNodeRadius+4]);
            // .size([this._treeCanvasHeightScale(this.model.forest.getCurrentTree(treeIndex).size), this._width - this._margin.left - 200]);
            let tree = this.model.forest.getCurrentTree(treeIndex);
            let currentRoot = layout(tree);
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

            this.legendOffset = Math.max(this.primary_legends[treeIndex].getLegendHeight(), this.secondary_legends[treeIndex].getLegendHeight());


            this.treeOffset = 0 + this.legendOffset + this._margin.top;

            //make an invisible rectangle for zooming on
            newg.append('rect')
                .attr('class', 'zoom-rect')
                .attr('height', currentLayoutHeight + this.treeOffset)
                .attr('width', this._width)
                .attr('fill', 'rgba(0,0,0,0)');

            //put tree itself into a group
            newg.append('g')
                .attr('class', 'chart')
                .attr('chart-id', treeIndex)
                .attr('height', globals.treeHeight)
                .attr('width', this._width)
                .attr('fill', 'rgba(0,0,0,0)');

            newg.style("display", "inline-block");

            //store node and link layout data for use later
            var treeLayout = layout(this.model.forest.getCurrentTree(treeIndex));
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

            newg.call(this.zoom)
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
        // this._aggNodeScale.domain([this.model.forest.aggregateMinMax[this.model.state.secondaryMetric].min, this.model.forest.aggregateMinMax[this.model.state.secondaryMetric].max]);

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
                // let layout = d3.tree().size([this._treeCanvasHeightScale(source.size), this._width - this._margin.left - 200]);
                let layout = d3.tree().nodeSize([this._maxNodeRadius+4, this._maxNodeRadius+4]);
                var treeLayout = layout(source);

                this.nodes[treeIndex] = treeLayout.descendants().filter(d=>{return !d.data.aggregate});
                this.aggregates[treeIndex] = treeLayout.descendants().filter(d=>{return d.data.aggregate});
                this.links[treeIndex] = treeLayout.descendants().slice(1);
                
                //recalculate layouts
                this._treeLayoutHeights[treeIndex] = this._getHeightFromTree(treeLayout);
                this._minmax[treeIndex] = this._getMinxMaxxFromTree(treeLayout);


                //THIS MUST COME AFTER this._minmax update!!
                this._calcNodePositions(treeLayout.descendants(), treeIndex);

                //only update after last tree
                if(treeIndex == this.model.forest.numberOfTrees - 1){
                    this.model.state.hierarchyUpdated = false;
                }

                this.newDataFlag = 1;
            }

            
            var chart = this.svg.selectAll('.group-' + treeIndex);
            var treeGroup = chart.selectAll('.chart');

            if(this.model.state.resetView == true){
                /**
                 * BUG - D3 TRANSFORM EVENET DOES NOT UPDATE
                 */
                treeGroup.attr("transform", "");

                chart.call(this.zoom.transform, d3.zoomIdentity);

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


            var standardNodes = treeGroup.selectAll(".node")
                    .data(this.nodes[treeIndex], (d) =>  {
                        return d.data.metrics._hatchet_nid || d.data.id;
                    });

            var aggNodes = treeGroup.selectAll(".aggNode")
                    .data(this.aggregates[treeIndex], (d) =>  {
                        return d.data.metrics._hatchet_nid || d.data.id;
                    });

            // links
            var links = treeGroup.selectAll("path.link")
                    .data(this.links[treeIndex], (d) =>  {
                        return d.data.metrics._hatchet_nid || d.data.id;
                    });
                

            // Enter any new links at the parent's previous position.
            links.enter()
                .append("path")
                .attr("class", "link")
                .attr("d", (d) =>  {
                    return this.diagonal(d, d.parent, treeIndex);
                })
                .attr('fill', 'none')
                .attr('stroke', '#ccc')
                .attr('stroke-width', '2px');

            
                        
                var aggNodeEnter = aggNodes.enter().append('g')
                .attr('class', 'aggNode')
                .attr("transform", (d) =>  {
                    return `translate(${this._treeDepthScale(d.depth)}, ${this._getLocalNodeX(d.x, treeIndex)})`;
                })
                .on('mouseover', function (d){
                    let ndgrp = d3.select(this);
                    ndgrp.selectAll("text")
                                    .text((d)=>{
                                        let n = "";
                                    
                                        if (d.data.elided.length == 1){
                                            n = `${d.data.prototype.data.name} Subtree`
                                        }
                                        else if(d.data.elided.length > 1){
                                            nodeStr = `Children of: ${d.parent.data.name}`
                                        }
                                        if (n.includes("<unknown file>")){
                                            n = n.replace('<unknown file>', '');
                                        }
                                        if (n.includes("<unknown procedure>")){
                                            n = n.replace('<unknown procedure>', '');
                                        }
        
                                        return n;
                                    });

                let textBBox = ndgrp.select("text").node().getBBox();

                ndgrp.selectAll("rect")
                        .attr("visibility", 'visible')
                        .attr("width", textBBox.width+2)
                        .attr("height", textBBox.height+2)
                        .attr("x",textBBox.x-1)
                        .attr("y",textBBox.y-1)
                        .attr("stroke-width", "1px")
                        .attr("stroke", "rgb(30,30,30)");
                })
                .on('mouseout', function(d){
                        d3.select(this).selectAll("text")
                        .text("");

                        d3.select(this).selectAll("rect")                
                            .attr("visibility", 'hidden');
                })
                .on("click", (d) => {
                    console.log(d);
                    this.observers.notify({
                        type: globals.signals.CLICK,
                        node: [d]
                    })
                })
                .on('dblclick', (d) =>  {
                    this.observers.notify({
                        type: globals.signals.COLLAPSESUBTREE,
                        node: d
                    })
                });
              
            
            
            aggNodeEnter.append('rect')
                .attr('fill', 'rgba(255,255,255,1)')
                .attr("visibility", 'visible');

            aggNodeEnter.append("circle")
                    .attr('class', 'aggNodeCircle')
                    .attr('r', (d) => {return Math.min(areaToRad(this._nodeScale(d.data.aggregateMetrics[secondaryMetric])), this._maxNodeRadius);})
                    .attr("fill", (d) =>  {
                        return this.color_managers[treeIndex].calcAggColorScale(d.data);
                    })
                    .style("stroke-width", "1px")
                    .style("stroke", "black")
                    .attr('transform', function (d) {
                        let r = Math.min(areaToRad(self._nodeScale(d.data.aggregateMetrics[secondaryMetric])), self._maxNodeRadius);
                        return `translate(0, 0)`;
                    });

            let arrows = aggNodeEnter.append('path')
                        .attr('class', 'aggNodeArrow')
                        .attr('fill', '#000')
                        .attr('stroke', '#000')
                        .attr('d', (d)=>{
                                        let rad = Math.min(areaToRad(this._nodeScale(d.data.aggregateMetrics[secondaryMetric])), this._maxNodeRadius);

                                        return `m 0,0 
                                        l 0,${rad*2} 
                                        l ${rad}, ${-rad}, 
                                        l ${-rad},0 
                                        z`
                                    });
            
            arrows.attr('transform', function(d){
                let rad = Math.min(areaToRad(self._nodeScale(d.data.aggregateMetrics[secondaryMetric])), self._maxNodeRadius);
                return `translate(${rad*2},${-rad})`;
            });

            aggNodeEnter.append("text")
                        .attr("x", (d) => {
                            let rad = Math.min(areaToRad(this._nodeScale(d.data.aggregateMetrics[secondaryMetric])), this._maxNodeRadius);
                            return -(rad*2);
                        })
                        .attr("dy", ".5em")
                        .attr("text-anchor", (d) => {
                            return "end";
                        })
                        .text((d) => {
                           
                            return "";
                        })
                        .style("font", "12px monospace")
                        .style('fill','rgba(0,0,0,.9)');
            
            


            // Enter any new nodes at the parent's previous position.
            var nodeEnter = standardNodes.enter()
                    .append('g')
                    .attr('class', 'node')
                    .attr("transform", (d) => {
                        return `translate(${this._treeDepthScale(d.depth)}, ${this._getLocalNodeX(d.x, treeIndex)})`;
                    })
                    .on('mouseover', function (d){
                        let ndgrp = d3.select(this);

                        if(!((d.data.text === undefined) && (!d.children || d.children.length == 0))){   
                            ndgrp.selectAll("text")
                                            .text(()=>{
                                                let n = d.data.name;
                                                if (n.includes("<unknown file>")){
                                                    n = n.replace('<unknown file>', '');
                                                }
                                                if (n.includes("<unknown procedure>")){
                                                    n = n.replace('<unknown procedure>', '');
                                                }
                                                return n;
                                            });

                            let textBBox = ndgrp.select("text").node().getBBox();

                            ndgrp.selectAll("rect")
                                .attr("visibility", 'visible')
                                .attr("width", textBBox.width+2)
                                .attr("height", textBBox.height+2)
                                .attr("x",textBBox.x-1)
                                .attr("y",textBBox.y-1)
                                .attr("stroke-width", "1px")
                                .attr("stroke", "rgb(30,30,30)");
                
                        }
                    })
                    .on('mouseout', function(d){
                        if(!((d.data.text === undefined) && (!d.children || d.children.length == 0))){
                            d3.select(this).selectAll("text")
                            .text("");

                            d3.select(this).selectAll("rect")                
                                .attr("visibility", 'hidden');
                        }
                    });
            
            
            nodeEnter.append('rect')
                .attr('fill', 'rgba(255,255,255,1)')
                .attr("visibility", 'visible');
                
            nodeEnter.append("circle")
                    .attr('class', 'circleNode')
                    .style("fill", (d) => {
                        return this.color_managers[treeIndex].calcColorScale(d.data);
                    })
                    .attr('cursor', 'pointer')
                    .style('stroke-width', '1px')
                    .style('stroke', 'black')
                    .attr("r", (d, i) => {
                        return areaToRad(this._nodeScale(d.data.metrics[secondaryMetric]));
                    })
                    .on("click", (d) => {
                        console.log(d);
                        let data = [d];
                        if(d3.event.shiftKey){
                            if(this.model.state.selectedNodes.includes(d)){
                                let delndx = this.model.state.selectedNodes.indexOf(d);
                                this.model.state.selectedNodes.splice(delndx, 1);
                                data = this.model.state.selectedNodes;
                            }else{
                                data = data.concat(this.model.state.selectedNodes);
                            }
                        }
                        this.observers.notify({
                            type: globals.signals.CLICK,
                            node: data
                        })
                    })
                    .on('dblclick', (d) =>  {
                        if(d3.event.ctrlKey){
                            this.observers.notify({
                                type: globals.signals.COMPOSEINTERNAL,
                                node: d
                            });
                        }
                        else{
                            this.observers.notify({
                                type: globals.signals.COLLAPSESUBTREE,
                                node: d
                            });
                        }
                    });


            nodeEnter.append("text")
                        .attr("x", (d) => {
                            return d.children || this.model.state['collapsedNodes'].includes(d) ? -13 : areaToRad(this._nodeScale(d.data.metrics[secondaryMetric])) + 5;
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
                                if (n.includes("<unknown procedure>")){
                                    n = n.replace('<unknown procedure>', '');
                                }
                                return n;
                            }
                            return "";
                        })
                        .style("font", "12px monospace")
                        .style('fill','rgba(0,0,0,.9)');
            
                        

            //add pluses to super_nodes
            let p_edge = 3;
            let s_depth = 4;
            nodeEnter.append("path")
                    .attr('d', `M 0,${s_depth}
                                h ${s_depth}
                                v -${s_depth}
                                h ${p_edge}
                                v ${s_depth}
                                h ${s_depth}
                                v ${p_edge}
                                h -${s_depth}
                                v ${s_depth}
                                h -${p_edge}
                                v -${s_depth}
                                h -${s_depth}
                                v -${p_edge}
                                z`)
                    .attr("visibility", "hidden")
                    .attr("fill", 'rgb(180,0,0)')
                    .on('dblclick', (d)=>{
                        this.observers.notify({
                            type: globals.signals.DECOMPOSENODE,
                            node: d
                        })
                    });


            // ---------------------------------------------
            // Updates 
            // ---------------------------------------------
            
            // Chart updates

            chart
                .transition()
                .duration(globals.duration)
                .attr("transform", () => {
                    if(this.model.state["activeTree"].includes(this.model.forest.rootNodeNames[treeIndex])){
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
                    else if(this.model.state["activeTree"].includes(this.model.forest.rootNodeNames[treeIndex])){
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
            links.transition()
                    .duration(globals.duration)
                    .attr("d", (d) => {
                        return this.diagonal(d, d.parent, treeIndex);
                    });

            // Transition normal nodes to their new position.
            standardNodes.transition()
                .duration(globals.duration)
                .attr("transform", (d) => {
                    return `translate(${this._treeDepthScale(d.depth)}, ${this._getLocalNodeX(d.x, treeIndex)})`;
                });
                    
            //update other characteristics of nodes
            standardNodes.select('circle.circleNode')
                .style('stroke', (d) => {
                        return 'black';
                })
                .style('stroke-width', (d) => {
                    if (this.model.state['selectedNodes'].some(n => n.data.id == d.data.id)){
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
                    return areaToRad(this._nodeScale(d.data.metrics[secondaryMetric]));
                })
                .style('fill', (d) => {
                    return this.color_managers[treeIndex].calcColorScale(d.data);

                });
            
            if(this.newDataFlag){
                standardNodes.select("text")
                    .attr("x", (d) => {
                        return d.children || this.model.state['collapsedNodes'].includes(d) ? -13 : areaToRad(this._nodeScale(d.data.metrics[secondaryMetric])) + 5;
                    })
                    .attr("dy", ".5em")
                    .attr("text-anchor", (d) => {
                        return d.children || this.model.state['collapsedNodes'].includes(d) ? "end" : "start";
                    })
                    .text((d) => {
                        if((d.data.text === undefined) && (!d.children || d.children.length == 0)){
                            let n = d.data.name;
                            if (n.includes("<unknown file>")){
                                n = n.replace('<unknown file>', '');
                            }
                            return n;
                        }
                        return "";
                    });
            }


            standardNodes.filter(function(d){ return d.data.composed != undefined})
                        .selectAll("path")
                        .attr('visibility', 'visible')
                        .transition()
                        .duration(globals.duration)
                        .attr('transform',function(d){
                            let rad = areaToRad(self._nodeScale(d.data.metrics[secondaryMetric]));
                            return `translate(${s_depth},${(-rad*2 - s_depth)})`
                        });
            
            standardNodes.filter(function(d){ return d3.select(this).select('path').attr('visibility') == 'visible' && d.data.composed == undefined})
                        .selectAll("path")
                        .attr('visibility', 'hidden')

            
            aggNodes
                .transition()
                .duration(globals.duration)
                .attr("transform", function (d) {
                        return `translate(${self._treeDepthScale(d.depth)}, ${self._getLocalNodeX(d.x, treeIndex)})`;
                });


            aggNodes
                .select('.aggNodeCircle')
                .attr('r', (d) => {return  Math.min(areaToRad(self._nodeScale(d.data.aggregateMetrics[secondaryMetric])), self._maxNodeRadius);})
                .style('stroke-width', (d) => {
                    if (this.model.state['selectedNodes'].includes(d)){
                        return '3px';
                    } 
                    else {
                        return '1px';
                    }
                })
                .style('fill', (d) =>  {
                    return this.color_managers[treeIndex].calcAggColorScale(d.data);
                })
                .attr('transform', function (d) {
                    let r = Math.min(areaToRad(self._nodeScale(d.data.aggregateMetrics[secondaryMetric])), self._maxNodeRadius);
                    return `translate(0, 0)`;
                });

            aggNodes
                .select('.aggNodeArrow')
                .attr('d', (d)=>{
                    let rad = Math.min(areaToRad(self._nodeScale(d.data.aggregateMetrics[secondaryMetric])), self._maxNodeRadius)-1;

                    return `m 0,0 
                    l 0,${rad*2} 
                    l ${rad}, ${-rad}, 
                    l ${-rad},0 
                    z`
                })
                .attr('transform', function(d){
                    let rad = Math.min(areaToRad(self._nodeScale(d.data.aggregateMetrics[secondaryMetric])), self._maxNodeRadius);
                    return `translate(${rad*2},${-rad})`
                });

            
                    
            // ---------------------------------------------
            // Exit
            // ---------------------------------------------
            // Transition exiting nodes to the parent's new position.
            var nodeExit = standardNodes.exit()
                .transition()
                .duration(globals.duration)
                .attr("transform", (d) =>  {
                    return "translate(" + this._treeDepthScale(d.parent.depth) + "," + this._getLocalNodeX(d.parent.x, treeIndex) + ")";
                })
                .remove();

            
            aggNodes.exit()
                .remove();

            // Transition exiting links to the parent's new position.
            links.exit().transition()
                .duration(globals.duration)
                .attr("d", (d) =>  {
                    return this.diagonal(d.parent, d.parent, treeIndex);
                })
                .remove();

            // make canvas always fit tree height
            if(this.model.state["activeTree"].includes("Show all trees") || this.model.state["activeTree"].includes(this.model.forest.rootNodeNames[treeIndex])){
                this.chartOffset = this._treeLayoutHeights[treeIndex] + this.treeOffset + this._margin.top;
                this._height += this.chartOffset;
            }

            if(standardNodes.size() > nodeEnter.size()){
                this.manageLabelCollisions(standardNodes);
            }
            else{
                this.manageLabelCollisions(nodeEnter);
            }
        }                    

        this.svg.attr("height", this._height);
    }
}

export default ChartView;