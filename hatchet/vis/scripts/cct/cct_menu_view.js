import { makeSignaller, d3, globals } from "./cct_globals";
import View from "../utils/view";


class MenuView extends View{
    /**
     * View class for the menu portion of the visualization
     * 
     * @param {DOMElement} elem - The current cell of the calling jupyter notebook
     * @param {Model} model - The model object
     */
    constructor(elem, model){
        super(elem, model);

        this._svg = null;
        this._svgButtonOffset = 0;

        this.width = elem.clientWidth - globals.layout.margin.right - globals.layout.margin.left;
        this.height = globals.treeHeight * (model.data["numberOfTrees"] + 1);

        this._preRender();
    }


    _addNewMenuButton(id, text, click){
        /**
         * Function created to remove some repeated code blocks and make it
         *  easier to add SVG buttons with a more dynamic left offset.
         * 
         * @param {string} id - The HTML id which will be affixed to the newly created button
         * @param {string} text - The text to be displayed on the button itself
         * @param {function} click - Callback function to be called on click of button.
         */
        var buttonPad = 5;
        var textPad = 3;

        var button = this._svg.append('g')
            .attr('id', id)
            .append('rect')
            .attr('height', '15px')
            .attr('x', this._svgButtonOffset).attr('y', 0).attr('rx', 5)
            .style('fill', '#ccc')
            .on('click', click);

        var buttonText = d3.select(this.elem).select('#'+id).append('text')
                .attr("x", this._svgButtonOffset + textPad)
                .attr("y", 12)
                .text(text)
                .attr("font-family", "sans-serif")
                .attr("font-size", "12px")
                .attr('cursor', 'pointer')
                .on('click', click);
        
        var width = buttonText.node().getBBox().width + 2*textPad;
            
        button.attr('width', width);

        this._svgButtonOffset += width + buttonPad;
    }


    _preRender(){
        const self = this;
        const model = this.model;
        let rootNodeNames = model.data["rootNodeNames"];
        let metricColumns = model.data["metricColumns"];

        const htmlInputs = d3.select(this.elem).insert('div', '.canvas').attr('class','html-inputs');

        //---------------------------------
        // HTML Interactables
        //---------------------------------

        htmlInputs.append('label').attr('for', 'primaryMetricSelect').text('Color by:');
        htmlInputs.append("select") 
                .attr("id", "primaryMetricSelect")
                .selectAll('option')
                .data(metricColumns)
                .enter()
                .append('option')
                .text(d => d)
                .attr('value', d => d)
                .style('margin', "10px 10px 10px 0px");

        htmlInputs.append('label').attr('for', 'secondaryMetricSelect').text('Size:');
        htmlInputs.append("select") 
                .attr("id", "secondaryMetricSelect")
                .selectAll('option')
                .data(metricColumns)
                .enter()
                .append('option')
                .attr('selected', (_,i) => i == 1 ? "selected" : null)
                .text(d => d)
                .attr('value', d => d)
                .style('margin', "10px 10px 10px 0px");


        htmlInputs.append('label').style('margin', '0 0 0 10px').attr('for', 'treeRootSelect').text(' Display:');
        htmlInputs.append("select") //element
                .attr("id", "treeRootSelect")
                .on('change', function () {
                    self.observers.notify({
                        type: globals.signals.TREECHANGE,
                        display: this.value
                    });
                })
                .selectAll('option')
                .data(rootNodeNames)
                .enter()
                .append('option')
                .attr('selected', d => d.includes('Show all trees') ? "selected" : null)
                .text(d => d)
                .attr('value', (d, i) => i + "|" + d)
                .style('margin', "10px 10px 10px 0px");
                
                
        
        
        htmlInputs.append('label').style('margin', '0 0 0 10px').attr('for', 'enable-pruning').text(' Enable Automatic Pruning:');
        htmlInputs
            .append("div")
            .style("display", "inline-block")
            .append('input')
            .attr('id', 'enable-pruning')
            .attr('type', 'checkbox')
            .style('margin-left', '10px')
            .on('click', function(){
                self.observers.notify({
                    type: globals.signals.ENABLEMASSPRUNE,
                    checked: d3.select(this).property('checked'),
                    threshold: d3.select(self.elem).select('#pruning-slider').node().value
                })
            });
        
        
        let sliderText = htmlInputs.append('label').style('margin', '0 0 0 10px').attr('for', 'pruning-slider').text(' Pruning Strictness (1.5):');
        htmlInputs
            .append("div")
                .attr("class", "slide-container")
                .style("width", "150px")
                .append("input")
                    .attr("id", "pruning-slider")
                    .attr("type", "range")
                    .attr("step", ".25")
                    .attr("min", "0")
                    .attr("max", "2")
                    .attr("value", "1.5")
                    .style('margin-left', "10px")
                    .on('change', function(){
                        // Does not conform fully to MVC model
                        sliderText.text(()=>{
                            return ` Pruning Strictness (${this.value})`;
                        });

                        self.observers.notify({
                            type: globals.signals.REQUESTMASSPRUNE,
                            threshold: parseFloat(this.value)
                        });
                    })
            
        // ----------------------------------------------
        // Create SVG and SVG-based interactables
        // ----------------------------------------------

        //make an svg in the scope of our current
        // element/drawing space
        this._svg = d3.select(this.elem).append("svg").attr("class", "inputCanvas");
        
        //-----------------------------------
        // SVG Interactables
        //-----------------------------------

        this._addNewMenuButton('selectButton', 'Select nodes',  
            function () {
                self.observers.notify({
                    type: globals.signals.TOGGLEBRUSH
                })
            });
        
        this._addNewMenuButton('colorButton', 
            function(){
                return `Colors: ${model.data["colors"][model.state["colorScheme"]]}`;
            }, 
            function () {
                self.observers.notify({
                    type: globals.signals.COLORCLICK
                })
            });
        
        this._addNewMenuButton('unifyLegends', 
            function(){ 
                return `Legends: ${model.data["legends"][model.state["legend"]]}`;
            }, 
            function () {
                self.observers.notify({
                    type: globals.signals.LEGENDCLICK
                });
            });
        
        this._addNewMenuButton('resetZoom', 'Reset View', 
            function () {
                self.observers.notify({
                    type: globals.signals.RESETVIEW
                });
            });

        this._addNewMenuButton('snapshotQuery', 'Get Snapshot Query',
            function(){
                self.observers.notify({
                    type: globals.signals.SNAPSHOT
                })
            })
        
        this._svg.attr('height', '15px').attr('width', this.width);

        // ----------------------------------------------
        // Define and set d3 callbacks for changes
        // ----------------------------------------------
        let brush = d3.brush()
            .extent([[0, 0], [2 * this.width, 2 * (this.height + globals.layout.margin.top + globals.layout.margin.bottom)]])
            .on('brush', function(){
                self.observers.notify({
                    type: globals.signals.BRUSH,
                    selection: d3.event.selection,
                    end: false
                })
            })
            .on('end', function(){
                self.observers.notify({
                    type: globals.signals.BRUSH,
                    selection: d3.event.selection,
                    end: true
                })
            });
        
        //brush group
        d3.select("#mainG").append('g')
            .attr('class', 'brush')
            .call(brush);
        
            
        //When metricSelect is changed (metric_col)
        d3.select(this.elem).select('#primaryMetricSelect')
            .on('change', function () {
                self.observers.notify({
                    type: globals.signals.METRICCHANGE,
                    newMetric: this.value,
                    source: d3.select(this).attr('id')
                })
            });

        d3.select(this.elem).select('#secondaryMetricSelect')
            .on('change', function(){
                self.observers.notify({
                    type:globals.signals.METRICCHANGE,
                    newMetric: this.value,
                    source: d3.select(this).attr('id')
                })
            })
        
        this.brushButton = d3.select(this.elem).select('#selectButton');
        this.colorButton = d3.select(this.elem).select('#colorButton');
        this.unifyLegends = d3.select(this.elem).select('#unifyLegends');
        this.brushButtonText = this.brushButton.select('text');
        this.colorButtonText = this.colorButton.select('text');
        this.legendText = this.unifyLegends.select('text');
        this.sliderText = sliderText;
        this.brush = brush;
    }
    
    
    render(){
        /**
         * Core call for drawing menu related screen elements
         */
        const self = this;
        let model = this.model;
        let brushOn = model.state["brushOn"];
        let curColor = model.state["colorScheme"];
        let colors = model.data["colors"];
        let curLegend = model.state["legend"];
        let legends = model.data["legends"];

        let pruneEnabled = model.state["pruneEnabled"];

        d3.select(this.elem).selectAll('.brush').remove();

        //updates
        this.brushButton.style("fill", function(){ 
            if(brushOn > 0){
                return "black";
            }
            else{
                return "#ccc";
            }
        })
        .attr('cursor', 'pointer');

        this.brushButtonText.style("fill", function(){
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
            this._svg.select("#mainG").append('g')
                .attr('class', 'brush')
                .call(this.brush);
        } 

        this.colorButtonText
        .text(function(){
            return `Colors: ${colors[curColor]}`;
        });

        this.legendText
        .text(function(){
            return `Legends: ${legends[curLegend]}`;
        });

        this.colorButton.attr('width', this.colorButtonText.node().getBBox().width + 10);
        this.unifyLegends.attr('width', this.legendText.node().getBBox().width + 10);
        
        this.sliderText
            .style('visibility', ()=>{
                if(pruneEnabled){
                    return 'visible';
                }
                else{
                    return 'hidden';
                }
            });

        d3.select(this.elem).select('.slide-container')
            .style('display', () =>{
                if(pruneEnabled){
                    return 'inline-block';
                }
                else{
                    return 'none';
                }
            });
    }
}

export default MenuView;