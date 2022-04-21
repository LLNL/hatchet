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
        this.categories = ['Metrics', 'Display', 'Query']
        this.model_var_map = {};
        this.menu_tree = [];

        this.width = elem.clientWidth - globals.layout.margin.right - globals.layout.margin.left;
        this.height = globals.treeHeight * (model.forest.numberOfTrees + 1);

        this.menu_height = '2em';
        this.menu_bg_color = 'rgba(100,100,100,1)';
        
        //state things
        this.prior_submenu = null;
        this.model.state.menu_active = false;
        
        this._setUpMenuTree();
        this._renderMenuBar();
        this._preRender();
    }

    _makeSubmenuOption(text, type, options, model_var, callback){
        /**
         * Makes a data-based defintion of a submenu option which
         * can be used with d3 to make our menu.
         * @param {String} text - Text which will appear to the user on the submenu option
         * @param {String} type - Describes the type of submenu option: 'button', 'dropdown' or 'toggle'
         * @param {Array{String}} options - Array of strings which are the dropdown options
         *                                  for 'dropdown' buttons
         * @param {String} model_var - A key which accesses a variable in the model that our submenu option
         *                              state is dependant on, so active selections can be 'checkmarked', etc.
         * @param {Function} callback - A callback function which runs when a user clicks the submenu button,
         *                              or a dropdown option in the case of a 'dropdown' type
         */
        this.model_var_map[text] = model_var;
        if(options != null){
            return {'text':text, 'type':type, 'options':options, 'onselect':callback}
        }
        return {'text':text, 'type':type, 'onclick':callback}
    }

    _setUpMenuTree(){
        /**
         * Creates a hierarchical data structure which is used by the render functions to load
         * a dropdown menu. This data model supports three types of
         * interactions on buttons 'dropdown' (a list of options which users can click and select from),
         * 'click' (a generic button), 'toggle' (a single option toggle on/off)
         */
        let model = this.model;
        let rootNodeNames = model.forest.rootNodeNames;
        let metricColumns = model.forest.metricColumns;
        let colors = model.data["colors"];
        let legends = model.data["legends"];
        let self = this;

        this.categories.forEach(d=>{
            this.menu_tree[d] = [];
        })

        //add metrics submenu
        this.menu_tree.Metrics.push(
            this._makeSubmenuOption('Color (Primary Metric)', 'dropdown', 
                metricColumns, 
                'primaryMetric',
                function(evt_sel, val){
                    self.observers.notify({
                        type: globals.signals.METRICCHANGE,
                        newMetric: val,
                        source: "primary"
                    })
                }
            )
        );

        this.menu_tree.Metrics.push(
            this._makeSubmenuOption('Size (Secondary Metric)', 'dropdown', 
                metricColumns,
                'secondaryMetric',
                function(evt_sel, val){
                    self.observers.notify({
                        type: globals.signals.METRICCHANGE,
                        newMetric: val,
                        source: "secondary"
                    })
                }
            )
        );
        
        //add display submenu
        this.menu_tree.Display.push(
            this._makeSubmenuOption('Tree Select', 'dropdown', 
                rootNodeNames,
                'activeTree', 
                function (evt_sel, val) {
                    self.observers.notify({
                        type: globals.signals.TREECHANGE,
                        display: val
                    });
                }
            )
        )

        this.menu_tree.Display.push(
            this._makeSubmenuOption('Color Map', 'dropdown', 
                colors,
                'colorText',
                function (evt_sel, val) {
                    self.observers.notify({
                        type: globals.signals.COLORCLICK,
                        value: val
                    })
                }
            )
        )
        
        this.menu_tree.Display.push(
            this._makeSubmenuOption('Legends', 'dropdown', 
                legends,
                'legendText',
                function (evt_sel, val) {
                    self.observers.notify({
                        type: globals.signals.LEGENDCLICK,
                        value: val
                    });
                }
            )
        )
        
        this.menu_tree.Display.push(
            this._makeSubmenuOption('Reset View', 'button', 
                null,
                null,
                function (evt_sel) {
                    self.observers.notify({
                        type: globals.signals.RESETVIEW
                    })
                }
            )
        )

        //add query/filter
        this.menu_tree['Query'].push(
            this._makeSubmenuOption('Select Nodes', 'toggle', 
                null,
                'brushOn', 
                function (evt_sel) {
                    self.observers.notify({
                        type: globals.signals.TOGGLEBRUSH
                    })
                }
            )
        )
        this.menu_tree['Query'].push(
            this._makeSubmenuOption('Mass Prune', 'toggle', 
                null, 
                'pruneEnabled',
                function(evt_sel){
                    self.observers.notify({
                        type: globals.signals.ENABLEMASSPRUNE,
                        threshold: 1.5
                    })
                }
            )
        )
        this.menu_tree['Query'].push(
            this._makeSubmenuOption('Get Snapshot Query', 'button', 
                null,
                null, 
                function(evt_sel){
                    window.alert("Query describing your current tree has been stored.\n Please use: \n\n\t%cct_fetch_query <python_variable>\n\n to retrieve your query back to the notebook.")
                    self.observers.notify({
                        type: globals.signals.SNAPSHOT
                    })
                }
            )
        )
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

    _handleSubmenuVisibility(d){
        const self = this;
        let submenu = d3.select(self.elem).select(`.${d}-submenu`);
        if(self.model.state.menu_active && submenu.style('visibility') == 'hidden'){
            submenu.style('visibility', 'visible');
        }
        else{
            submenu.style('visibility', 'hidden');
        }
    }

    _renderMenuBar(){
        /**
         * Renders a windows/unix style top menu bar
         */

        //render a grey rectangle where categories sit
        // 2em tall, full width
        let menu_svg = d3.select(this.elem).append("svg").attr("class", "menu-svg");
        this._svg = menu_svg;
        const self = this;
        const buttonPad = 10;
        const bg_color = this.menu_bg_color;
        const menu_height = '2em';
        const text_v_offset = '1.4em';
        const vis_name_text = 'Interactive Calling Context Tree'

        menu_svg.attr('width', this.elem.clientWidth)
            .attr('height', menu_height)
        
        menu_svg.append('rect')
            .attr('width', this.elem.clientWidth)
            .attr('height', menu_height)
            .style('fill', bg_color);

        let vis_name = menu_svg
            .append('text')
            .text(vis_name_text)
            .attr('x', this.elem.clientWidth)
            .attr('y', 20)
            .attr("font-family", "sans-serif")
            .attr("font-size", "14px")
            .style('fill', 'rgba(256,256,256,1)');

        vis_name.attr('x', function(){
           return self.elem.clientWidth - d3.select(this).node().getBBox().width - 25;
        })

        let options = menu_svg
                        .selectAll('.option')
                        .data(this.categories);
        
        let op_grp = options.enter()
                            .append('g')
                            .attr('class', 'option')
                            .attr('cursor', 'pointer')
                            .on('mouseover',function(d){
                                d3.select(this)
                                    .select('.menu-button')
                                    .style('fill', 'rgba(150,150,150,1)');
                                if(self.model.state.menu_active && (d !== self.prior_submenu)){
                                    self._handleSubmenuVisibility(d);
                                    self._handleSubmenuVisibility(self.prior_submenu);
                                    self.prior_submenu = d;
                                }
                                
                            })
                            .on('mouseout', function(){
                                d3.select(this)
                                    .select('.menu-button')
                                    .style('fill', bg_color);
                            })
                            .on('click', function(d){
                                self.observers.notify({type: globals.signals.TOGGLEMENU});
                                self.prior_submenu = d;
                                self._handleSubmenuVisibility(d);
                            });
                            
        op_grp.append('rect')
                .attr('class','menu-button')
                .attr('height', menu_height)
                .style('fill', bg_color);
        
        op_grp.append('text')
                .text(d=>{return d})
                .attr('class','menu-text')
                .attr('y', text_v_offset)
                .attr('x', buttonPad)
                .attr("font-family", "sans-serif")
                .attr("font-size", "14px")
                .style('fill', 'rgba(256,256,256,1)');


        let offset = 0;
        op_grp.each(function(d){
            let btn_grp = d3.select(this);
            let btn_width = btn_grp.select(".menu-text").node().getBBox().width + 2*buttonPad
            
            //apply modified widths and offsets
            btn_grp.select(".menu-button")
                    .attr('width', btn_width)    
                    .style('stroke', 'black')
                    .style('stroke-dasharray', `0, ${btn_width}, ${menu_height}, ${btn_width}, ${menu_height}, 0`);
            btn_grp.attr('transform', `translate(${offset}, 0)`);
            self._addSubmenu(d, self.menu_tree[d], offset);

            offset += btn_width;

        })
    }

    _addSubmenu(submenu_name, submenu_options, x_offset){
        /**
         * Renders a submenu drop down under a top level menu button.
         */
        let view_left =  this.elem.getBoundingClientRect().left - this.elem.parentNode.getBoundingClientRect().left;
        let view_top = this._svg.select('rect').node().getBBox().height;
        const button_pad = 10;
        const self = this;

        let submenu_window = d3.select(this.elem)
                                .append('svg')
                                .style('position', 'absolute')
                                .style('top', view_top + 16 + 'px')
                                .style('left', view_left + x_offset + 5 + 'px')
                                .style('width', '600px')
                                .attr('class', `${submenu_name}-submenu`)
                                .style('visibility', 'hidden')
                                .append('g')
                                .attr('class', 'submenu-grp');

        let border = submenu_window.append('rect')
                        .attr('height', submenu_options.length*25)
                        .style('stroke', 'white')
                        .style('stroke-width', 2);
        
        let opt = submenu_window
                        .selectAll('.submenu-button')
                        .data(submenu_options);

        let btn = opt.enter()
                    .append('g')
                    .attr('class', 'submenu-button')
                    .attr('transform', (_,i)=>{return `translate(0, ${i*25+1})`})
                    .attr('cursor', 'pointer')
                    .on('mouseover',function(){
                        d3.select(this)
                            .select('.submenu-button-rect')
                            .style('fill', 'rgba(150,150,150,1)');
                    })
                    .on('mouseout', function(){
                        d3.select(this)
                            .select('.submenu-button-rect')
                            .style('fill', self.menu_bg_color);
                    })
                    .on('click', function(d){
                        if(d.type != 'dropdown') d.onclick(this);   
                    });
                

        let bar = btn.append('rect')
            .attr('class', 'submenu-button-rect')
            .attr('height', 25)
            .style('fill', this.menu_bg_color);


        btn.append('text')
            .text((d)=>{return d['text']})
            .attr('class', 'submenu-button-text')
            .attr('y', '1.2em')
            .attr('x', button_pad)
            .attr("font-family", "sans-serif")
            .attr("font-size", "14px")
            .style('fill', 'rgba(256,256,256,1)');

        let max_width = 0;
        btn.each(function(d){
            max_width = Math.max(this.getBBox().width, max_width);
        })

        let barwidth = max_width + 2*button_pad + 25;
        bar.attr('width', barwidth);
        border.attr('width', barwidth);

        btn.each(function(d){
            let this_button = d3.select(this);

            if(d.type == 'dropdown'){
                self._makeDropDownMenu(this_button, d.options, barwidth, d.onselect);
                
                this_button.on('mouseenter', function(){
                    let submenu = d3.select(this).select(`.cct-dropdown-menu`);
                    submenu.style('visibility', 'visible');
                })
                .on('mouseleave', function(){
                    let submenu = d3.select(this).select(`.cct-dropdown-menu`);
                    submenu.style('visibility', 'hidden');
                })
            }
        })

        btn.append('text')
            .text((d)=>{ if(d.type == 'dropdown') return '▸'; })
            .attr('class', 'submenu-icon')
            .attr('y', '1.2em')
            .attr('x', max_width + 25)
            .attr("font-family", "sans-serif")
            .attr("font-size", "14px")
            .style('fill', 'rgba(256,256,256,1)');               
    }

    _makeDropDownMenu(button, options, xoffset, callback){
        /**
         * Renders a list of options under a 'dropdown' submenu option.
         */
        let xorigin = xoffset;
        let yorigin = button.node().getBBox().y;
        let button_pad = 10;
        let self = this;
        let selections = button.append('g')
                                .attr('class', 'cct-dropdown-menu')
                                .attr('transform', `translate(${xorigin}, ${yorigin})`)
                                .style('visibility', 'hidden');

        selections.append('rect')
                .attr('height', options.length*25)
                .attr('width', 150)
                .style('stroke', 'white')
                .style('stroke-width', 2);

        let sel = selections.selectAll('.cct-dropdown-option')
                .data(options);
        
        let opt = sel.enter()
                    .append('g')
                    .attr('class', 'cct-dropdown-option')
                    .attr('transform', (_,i)=>{return `translate(0, ${i*25})`})
                    .attr('cursor', 'pointer')
                    .on('mouseenter', function(){
                        d3.select(this).select('.cct-dropdown-option-rect').style('fill', 'rgba(150,150,150,1)');
                    })
                    .on('mouseleave', function(){
                        d3.select(this).select('.cct-dropdown-option-rect').style('fill', self.menu_bg_color);
                    })
                    .on('click', function(d){
                        callback(this, d);
                    });

        opt.append('rect')        
            .attr('height', 25)
            .attr('width', 150)
            .attr('class', 'cct-dropdown-option-rect')
            .style('fill', this.menu_bg_color);

        opt.append('text')
            .text((d)=>{return d})
            .attr('class', 'cct-dropdown-option-text')
            .attr('y', '1.2em')
            .attr('x', button_pad)
            .attr("font-family", "sans-serif")
            .attr("font-size", "14px")
            .style('fill', 'rgba(256,256,256,1)');

        opt.append('text')
            .text((_, i)=>{ if(i == 0) return '✓'; })
            .attr('class', 'cct-dropdown-icon')
            .attr('y', '1.2em')
            .attr('x', 130)
            .attr("font-family", "sans-serif")
            .attr("font-size", "16px")
            .style('fill', 'rgba(256,256,256,1)');      
    }

    _preRender(){
        const self = this;
   
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
        
        this.brush = brush;
    }
    
    
    render(){
        /**
         * Core call for drawing menu related screen elements
         */
        const self = this;
        let model = this.model;

        //toggleable events
        let pruneEnabled = model.state["pruneEnabled"];
        let brushOn = model.state["brushOn"];

        if(!model.state.menu_active && self.prior_submenu){
            let submenu = d3.select(self.elem).select(`.${self.prior_submenu}-submenu`);
            if(submenu.style('visibility') != 'hidden'){
                submenu.style('visibility', 'hidden');
            }
        }

        for(let option of this.categories){
            let submenuopts = d3.select(this.elem)
                                .select(`.${option}-submenu`)
                                .selectAll('.submenu-button');
                                
            submenuopts.each(
                function(d){
                    let dropdownopts = d3.select(this).selectAll(`.cct-dropdown-option`);
                    dropdownopts
                        .selectAll('.cct-dropdown-icon')
                        .text((v)=>{
                            if(model.state[self.model_var_map[d.text]] == v){
                                return ('✓');
                            }
                            return ('');
                        });

                    if(d.type == 'toggle'){
                        if(pruneEnabled && d.text == 'Mass Prune'){
                            d3.select(this).select('.submenu-icon').text('✓');
                        }else if(!pruneEnabled && d.text == 'Mass Prune'){
                            d3.select(this).select('.submenu-icon').text('');
                        }

                        else if(d.text == 'Select Nodes'){
                            if(brushOn > 0){
                                d3.select(this).select('.submenu-icon').text('✓');
                            }
                            else if(brushOn < 0){
                                d3.select(this).select('.submenu-icon').text('');
                            }
                        }
                    }
                }
            )
        }

        d3.select(this.elem).selectAll('.brush').remove();

        //add brush if there should be one
        if(brushOn > 0){
            this._svg.select("#mainG").append('g')
                .attr('class', 'brush')
                .call(this.brush);
        } 

    }
}

export default MenuView;