import View from '../utils/view';
import {d3, globals, getSigFigString} from './cct_globals';

class ScentedSliderPopup extends View{

    constructor(elem,model){
        super(elem, model);
        this.popup_dims = {
            'width': 350,
            'height': 200,
            'left_padding': 45,
            'right_padding': 30,
            'top_padding': 30
        }
        this.full_hist_height = this.popup_dims.height*.5;
        this.num_bins = 25;
        this.slider_width = 10;
        this.slider_height = 20;
        this.dropdown_clicked = false;

        this._svg = d3.select(elem)
                        .append('svg')
                        .attr('width', this.popup_dims['width'])
                        .attr('height', this.popup_dims['height'])
                        .style('overflow', 'visible')
                        .style('position', 'absolute')
                        // .style('left', (this.elem.clientWidth*.5 - this.popup_dims.width*.5) + 'px')
                        .style('left', '145px')
                        .style('top', '150px')
                        .style('visibility', 'hidden');

        model.updateBins(this.num_bins);
        this.bins = model.data.distCounts["nonzero"];
        this.zero_bins = model.data.distCounts["internalzero"]
       
        this.update_bin_count_ranges();

        if(this.max_zero_cnt > 0){
            this.hist_height = this.full_hist_height*.7;
            this.icycle_height = this.full_hist_height-this.hist_height;
        }
        else{
            this.hist_height = this.full_hist_height;
            this.icycle_height = 0;
        }

        this.slider_range = model.forest.forestMetrics[model.state.primaryMetric];
        this.h_x_scale = d3.scaleLinear().domain([0,this.bins.length]).range([0, this.popup_dims['width']-this.popup_dims.left_padding-this.popup_dims.right_padding]);
        this.h_y_scale = d3.scaleLinear().domain(this.bin_count_range).range([4, this.hist_height]);
        this.invert_y_scale = d3.scaleLinear().domain(this.bin_count_range).range([this.hist_height, 0]);
        this.i_y_scale = d3.scaleLinear().domain([0, this.max_zero_cnt]).range([0, this.icycle_height]);

        //for communicating that sliding is over
        this.update = false;

        this.pre_render();
        this.render();
    }
    
    update_bin_count_ranges(){
        /**
         * Update the minimum and maximum ranges of values across all
         * bins in the histogram. Used for mainting the y scale of the
         * histogram.
         */
        this.bin_count_range = [Number.MAX_VALUE, Number.MIN_VALUE];

        this.max_zero_cnt = 0;
        this.zero_bins.forEach((b)=>{this.max_zero_cnt = Math.max(b.length, this.max_zero_cnt)});

        this.bins.forEach(d=>{
            this.bin_count_range[0] = Math.min(d.length, this.bin_count_range[0]);
            this.bin_count_range[1] = Math.max(d.length, this.bin_count_range[1]);
        })
    }

    manage_slider_update(slider, x_pos){
        /**
         * Callback function which manages updating the data and state associated with
         * the histogram sliders.
         */
        const self = this;
        let bin_num = parseInt(self.h_x_scale.invert(x_pos+this.slider_width/2));
        let range_val = 0;
        let step_loc = 0;
        let update = false;

        if(slider.attr("class").includes('l-slider-grp')){
            if(bin_num < self.bins.length){
                range_val = self.bins[bin_num].x0;
                if(bin_num != this.current_l_bin && bin_num <= this.current_r_bin){
                    step_loc = self.h_x_scale(bin_num);
                    this.current_l_bin = bin_num;
                    update = true;
                }
            }
        }
        else{
            if(bin_num < self.bins.length){
                range_val = self.bins[bin_num].x1;
                if(bin_num != this.current_r_bin && bin_num >= this.current_l_bin){
                    step_loc = self.h_x_scale(bin_num+1);
                    this.current_r_bin = bin_num;
                    update = true;
                }
            }
        }


        if(update){
            self.update = true;
            slider.attr('transform', `translate(${step_loc-self.slider_width/2},0)`);
            slider.select('text').text(`${getSigFigString(range_val)}`);
            slider.select('text').attr('x', function(){return -(this.getBBox().width/2) + self.slider_width/2});
        }
    }

    handle_range_drag(sld_node){
        /**
         * Routing function which enables the correct
         * slider update arguments to be called depending on the location of the sliders.
         */

        let slider = d3.select(sld_node);
        const self = this;

        slider.attr('cursor','grabbing');
        if(d3.event.x > self.l_slider_pos_origin && d3.event.x < self.r_slider_pos_origin){
            self.manage_slider_update(slider, d3.event.x);
        }
        else if (d3.event.x < self.l_slider_pos_origin){
            self.manage_slider_update(slider, self.l_slider_pos_origin);
        }
        else if (d3.event.x > self.r_slider_pos_origin){
            self.manage_slider_update(slider, self.r_slider_pos_origin);
        }
    }

    pre_render(){
        const self = this;

        var start_x = 0;
        var start_y = 0;

        //Define drag functionality for the whole popup
        let windowDragHandler = d3.drag()
                            .on("end", function(){
                                d3.select(this)
                                    .attr('cursor','grab');
                            })
                            .on("drag", function(){
                                d3.select(this).attr('cursor','grabbing');
                                self._svg.style('left', parseInt(self._svg.style('left').slice(0,-2)) + d3.event.x-start_x + 'px');
                                self._svg.style('top', parseInt(self._svg.style('top').slice(0,-2)) + d3.event.y-start_y + 'px');
                            })
                            .on("start", function(){
                                self.update = false;
                                start_x = d3.event.x;
                                start_y = d3.event.y;
                            });


        //render histogram
        this._svg.append('rect')
                    .attr('height', this.popup_dims['height'])
                    .attr('width', this.popup_dims['width'])
                    .attr('fill', 'rgba(255,255,255,1)')
                    .attr('stroke', 'rgba(0,0,0,1)')
                    .attr('stroke-width', 2);
        
        let topBar = this._svg.append('rect')
                    .attr('height', '2em')
                    .attr('width', this.popup_dims['width'])
                    .attr('fill', 'rgba(255,255,255,0)')
                    .attr('stroke', 'rgba(0,0,0,1)')
                    .attr('stroke-width', 1)
                    .attr('cursor', 'grab');

        windowDragHandler(topBar);

        this._svg.append('text')
                    .text(`Prune over "${this.model.state.primaryMetric}" metric distribution.`)
                    .attr('id', 'slider-header')
                    .attr('fill', 'rgba(0,0,0,1)')
                    .attr('y', 20)
                    .attr('x', 5);
        
        this._svg.append('text')
                    .text('')
                    .attr('fill', 'rgba(0,0,0,1)')
                    .attr('y', 20)
                    .attr('x', this.popup_dims['width']-10);
                
        this._svg.append('g')
                    .attr('class', 'hist-grp')
                    .attr('height', this.hist_height)
                    .attr('width', this.popup_dims['width'])
                    .attr('transform', `translate(${this.popup_dims.left_padding}, ${this.popup_dims.top_padding+5})`);
    
        this._svg.append('g')
                    .attr('class', 'ice-grp')
                    .attr('height', this.icycle_height)
                    .attr('width', this.popup_dims['width'])
                    .attr('transform', `translate(${this.popup_dims.left_padding},${this.popup_dims.top_padding+5+this.hist_height})`)

        this.hist_grp = this._svg.select('.hist-grp');
        this.ice_grp = this._svg.select('.ice-grp');

        this.hist_grp.append('g')
                        .attr('class', 'left-axis')
                        .attr('transform', `translate(0, 0)`)
                        .call(d3.axisLeft(this.invert_y_scale).ticks(4));

        this.ice_grp.append('g')
                    .attr('class', 'left-ice-axis')
                    .call(d3.axisLeft(this.i_y_scale).ticks(4));

        this.l_slider_pos_origin = -(this.slider_width/2);
        this.r_slider_pos_origin = this.popup_dims['width']-this.popup_dims.left_padding - this.popup_dims.right_padding - (this.slider_width/2);
        this.current_l_bin = parseInt(this.h_x_scale.invert(this.l_slider_pos_origin));
        this.current_r_bin = parseInt(this.h_x_scale.invert(this.r_slider_pos_origin));

        let dragHandler = d3.drag()
                            .on("end", function(){
                                if(self.update){
                                    self.observers.notify({
                                        type: globals.signals.PRUNERANGEUPDATE,
                                        low: self.bins[self.current_l_bin].x0,
                                        high: self.bins[self.current_r_bin].x1
                                    });
                                    self.update = false;
                                }
                                d3.select(this)
                                    .attr('cursor','grab');
                            })
                            .on("drag", function(){
                                self.handle_range_drag(this);
                            })
                            .on("start", function(){
                                self.update = false;
                            });

        let l_slider = this.hist_grp.append('g')
                                .attr('class', 'l-slider-grp')
                                .attr('transform', `translate(${this.l_slider_pos_origin},0)`)
                                .attr('cursor', 'grab');
                    
        l_slider.append('rect')
                        .attr('class', 'left-handle')
                        .attr('width', this.slider_width)
                        .attr('height', this.slider_height)
                        .attr('y', this.full_hist_height+2)
                        .attr('fill', 'rgba(200,150,150,1)')
                        .attr('stroke', 'rgba(0,0,0,1)');

        l_slider.append('line')
                    .attr('class', 'left-line')
                    .attr('x1', (this.slider_width/2))
                    .attr('x2', (this.slider_width/2))
                    .attr('y1', 0)
                    .attr('y2', this.full_hist_height+2)
                    .attr('stroke', 'rgba(200,50,50,1)');

        let txt = l_slider.append('text')
                            .text(`${getSigFigString(this.bins[parseInt(this.h_x_scale.invert(this.l_slider_pos_origin))].x0)}`)
                            .attr('y', this.full_hist_height+2+this.slider_height+14);

        txt.attr('x', function(){return -(this.getBBox().width/2) + self.slider_width/2});
        

        let r_slider = this.hist_grp.append('g')
                                .attr('class', 'r-slider-grp')
                                .attr('transform', `translate(${this.r_slider_pos_origin},0)`)
                                .attr('cursor', 'pointer');
                
        r_slider.append('rect')
                        .attr('class', 'right-handle')
                        .attr('width', this.slider_width)
                        .attr('height', this.slider_height)
                        .attr('y', this.full_hist_height+2)
                        .attr('fill', 'rgba(200,150,150,1)')
                        .attr('stroke', 'rgba(0,0,0,1)');

        r_slider.append('line')
                    .attr('class', 'right-line')
                    .attr('x1', (this.slider_width/2))
                    .attr('x2', (this.slider_width/2))
                    .attr('y1', 0)
                    .attr('y2', this.full_hist_height+2)
                    .attr('stroke', 'rgba(200,50,50,1)');

        txt = r_slider.append('text')
                .text(`${getSigFigString(this.bins[parseInt(this.h_x_scale.invert(this.r_slider_pos_origin))].x1)}`)
                .attr('y', this.full_hist_height+2+this.slider_height+14);

        txt.attr('x', function(){return -(this.getBBox().width/2) + self.slider_width/2});
        
        dragHandler(l_slider);
        dragHandler(r_slider);
        

        //Selection box area
        let select_line = this._svg
                            .append('g')
                            .attr('class', 'distribution_selection')
                            .attr('transform', `translate(10, ${this.full_hist_height+this.slider_height+topBar.node().getBBox().height + 40})`);

        let info_txt = select_line.append('text')
                            .text('Current metric distribution: ');

        let select_box = select_line.append('g')
                                    .attr('class', 'selection-button')
                                    .attr('cursor', 'default')
                                    .on('mouseenter', function(){
                                        select_area
                                            .attr('fill', 'rgba(100,100,200,1)');
                                        self.current_selection_text.attr('fill', 'rgba(255,255,255,.9)');
                                    })
                                    .on('mouseleave', function(){
                                        if(!self.dropdown_clicked){
                                            select_area
                                                .attr('fill', 'rgba(255,255,255,1)');
                                            self.current_selection_text
                                                .attr('fill', 'rgba(0,0,0,.9)');
                                        }
                                    })
                                    .on('click', function(){
                                        self.dropdown_clicked = !self.dropdown_clicked;
                                        if(self.dropdown_clicked){
                                            select_area
                                                .attr('fill', 'rgba(100,100,200,1)');
                                            self.current_selection_text.attr('fill', 'rgba(255,255,255,.9)');
                                            self.options_dropdown.style('visibility', 'visible');
                                        }
                                        else{
                                            select_area
                                                .attr('fill', 'rgba(255,255,255,1)');
                                            self.current_selection_text.attr('fill', 'rgba(0,0,0,.9)');
                                            self.options_dropdown.style('visibility', 'hidden');
                                        }
                                    });
        
        let select_area = select_box.append('rect')
            .attr('y', ()=>{return -info_txt.node().getBBox().height;})
            .attr('x',  info_txt.node().getBBox().width + 10)
            .attr('fill', 'rgba(255,255,255,1)')
            .attr('stroke', 'rgba(0,0,0,1)')
            .attr('stroke-width', 1);

        this.current_selection_text = select_box.append('text')
            .text(()=>{return this.model.state.primaryMetric})
            .attr('x', ()=>{return info_txt.node().getBBox().width + 12;});

        this.options_dropdown = select_box.append('g')
                                            .style('visibility', 'hidden');

        select_area.attr('height', ()=>{return this.current_selection_text.node().getBBox().height+4})
                    .attr('width', ()=>{return this.current_selection_text.node().getBBox().width+10});      
                                                  

        
                

    }

    render(){
        const self = this;
        let options = this.model.forest.metricColumns;
        this.bins = this.model.data.distCounts["nonzero"];
        this.zero_bins = this.model.data.distCounts["internalzero"];
        this.update_bin_count_ranges();

        this.h_y_scale.domain(this.bin_count_range);
        this.invert_y_scale.domain(this.bin_count_range);
        this.h_x_scale.domain([0, this.bins.length]);
        this.i_y_scale.domain([0, this.max_zero_cnt]);


        this._svg.style('visibility', ()=>{
            if(this.model.state.pruneEnabled) return 'visible';
            return 'hidden';
        });


        this._svg.select('#slider-header')
                .text(`Prune over "${this.model.state.primaryMetric}" metric distribution.`)

        let bars = this.hist_grp.selectAll('.hist-bar')
            .data(this.bins);  
        
        let rev_bars = this.ice_grp.selectAll('.ice-bar')
            .data(this.zero_bins);
        
        let met_options = this.options_dropdown.selectAll('.metric-option')
            .data(options)

        /**
         * 
         * ENTER
         * 
         */

                
        let sel_btn_bbx = this._svg.select('.selection-button').node().getBBox();
        let max_option_width = 0;
        let max_option_height = 0;

        let option_button = met_options.enter()
                            .append('g')
                            .attr('class', 'metric-option')
                            .attr('transform', (_,i)=>{
                                return `translate(${sel_btn_bbx.x}, ${i*sel_btn_bbx.height + sel_btn_bbx.height/4})`
                            })
                            .on('click',  function(d){
                                self.observers.notify({
                                    type: globals.signals.METRICCHANGE,
                                    newMetric: d,
                                    source: "primary"
                                });
                            })
                            .on('mouseenter',function(){
                                d3.select(this).select('rect').attr('fill', 'rgba(100,100,200,1)');
                                d3.select(this).select('text').attr('fill', 'rgba(255,255,255,.9)');
                            })
                            .on('mouseleave',function(){
                                d3.select(this).select('rect').attr('fill', 'rgba(255,255,255,1)');
                                d3.select(this).select('text').attr('fill', 'rgba(0,0,0,.9)');
                            });
                           

            
        let option_rects = option_button.append('rect')
                            .attr('height', sel_btn_bbx.height)
                            .attr('fill', 'rgba(255,255,255,1)')
                            .attr('stroke', 'rgba(0,0,0,1)')
                            .attr('stroke-width', 1);
                               
        let opt_txt = option_button.append('text')
                     .text((d)=>{return d})
                     .attr('x', 2);
        
        opt_txt.each(function(){
            max_option_width = Math.max(this.getBBox().width, max_option_width);
            max_option_height = Math.max(this.getBBox().height, max_option_height);


            d3.select(this).attr('y', sel_btn_bbx.height/2 + this.getBBox().height/2 );
        })
    

        bars.enter()
            .append('rect')
            .attr('class', 'hist-bar')
            .attr('width', (this.popup_dims['width']-this.popup_dims.left_padding-this.popup_dims.right_padding)/this.bins.length)
            .attr('height', d => {
                if(d.length != 0){
                    return this.h_y_scale(d.length);
                } 
                return 0;
            })
            .attr('x', (_,i)=>{return this.h_x_scale(i)})
            .attr('y', (d)=>{
                if(d.length != 0){
                    return (this.hist_height-this.h_y_scale(d.length)) //- v_bar_negative_padding;
                }
                return this.hist_height;
            })
            .attr('fill', (_,i)=>{
                if(i >= this.current_l_bin && i <= this.current_r_bin){
                    return 'rgba(100,100,200,1)';
                }
            })
            .attr('stroke','rgba(0,0,0,1)')
            .attr('stroke-width', '1px')
            .on('mouseenter',(d)=>{
                this.observers.notify({
                    type: globals.signals.UPDATESELECTED,
                    nodes: d
                });
            })
            .on('mouseleave', ()=>{
                this.observers.notify({
                    type: globals.signals.UPDATESELECTED,
                    nodes: []
                });
            });

    
        rev_bars.enter()
            .append('rect')
            .attr('class', 'ice-bar')
            .attr('width', (this.popup_dims['width']-this.popup_dims.left_padding-this.popup_dims.right_padding)/this.bins.length)
            .attr('height', d => {
                if(d.length != 0){
                    return this.i_y_scale(d.length);
                } 
                return 0;
            })
            .attr('x', (_,i)=>{return this.h_x_scale(i)})
            .attr('y', 0)
            .attr('fill', (_,i)=>{
                return 'rgba(200,200,200,1';
            })
            .attr('stroke','rgba(0,0,0,1)')
            .attr('stroke-width', '1px')
            .on('mouseenter',(d)=>{
                this.observers.notify({
                    type: globals.signals.UPDATESELECTED,
                    nodes: d
                });
            })
            .on('mouseleave', ()=>{
                this.observers.notify({
                    type: globals.signals.UPDATESELECTED,
                    nodes: []
                });
            });

        /**
         * 
         * UPDATE
         * 
         */

        this._svg.select('.selection-button')
                    .select('rect')
                    .attr('fill',  ()=>{
                        if(!self.dropdown_clicked){
                           return 'rgba(255,255,255,1)';
                        }
                        else{
                            return 'rgba(100,100,200,1)';
                        }
                    });

        this._svg.select('.selection-button')
                    .select('text')
                    .attr('fill',  ()=>{
                        if(!self.dropdown_clicked){
                            return 'rgba(0,0,0,.9)';
                        }
                        else{
                            return 'rgba(255,255,255,.9)';
                        }
                    });

        option_rects
            .attr('width', max_option_width + 10);
                        
        
        this.current_selection_text.text(this.model.state.primaryMetric);

        this.hist_grp.select('.left-axis')
                .transition()
                .duration(globals.duration)
                .call(d3.axisLeft(this.invert_y_scale).ticks(4));

        this.hist_grp.select('.left-ice-axis')
                .transition()
                .duration(globals.duration)
                .call(d3.axisLeft(this.i_y_scale).ticks(4));

        bars.attr('fill', (_,i)=>{
                if(i >= this.current_l_bin && i <= this.current_r_bin){
                    return 'rgba(100,100,200,1)';
                }
                return 'rgba(200,200,200,1';
            })
            .transition()
            .duration(750)
            .attr('width', (this.popup_dims['width']-this.popup_dims.left_padding-this.popup_dims.right_padding)/this.bins.length)
            .attr('height', d => {
                if(d.length != 0){
                    return this.h_y_scale(d.length);
                } 
                return 0;
            })
            .attr('x', (_,i)=>{return this.h_x_scale(i)})
            .attr('y', (d)=>{
                if(d.length != 0){
                    return (this.hist_height-this.h_y_scale(d.length)) //- v_bar_negative_padding;
                }
                return this.hist_height;
            });

        rev_bars
            .transition()
            .duration(750)
            .attr('width', (this.popup_dims['width']-this.popup_dims.left_padding-this.popup_dims.right_padding)/this.bins.length)
            .attr('height', d => {
                if(d.length != 0){
                    return this.i_y_scale(d.length);
                } 
                return 0;
            })
            .attr('x', (_,i)=>{return this.h_x_scale(i)});




        if(this.model.state.metricUpdated){
            this.current_l_bin = 0;
            this.current_r_bin = parseInt(self.h_x_scale.invert(this.r_slider_pos_origin));
            let l_step_loc = self.h_x_scale(this.current_l_bin);
            let r_step_loc = self.h_x_scale(this.current_r_bin+1);

            let l_slider = this._svg.select('.l-slider-grp');
            let r_slider = this._svg.select('.r-slider-grp');

            l_slider.attr('transform', `translate(${l_step_loc-(this.slider_width/2)},0)`);
            l_slider.select('text').text(`${getSigFigString(self.bins[this.current_l_bin].x0)}`);
            l_slider.select('text').attr('x', function(){return -(this.getBBox().width/2) + self.slider_width/2});

            r_slider.attr('transform', `translate(${r_step_loc-(this.slider_width/2)},0)`);
            r_slider.select('text').text(`${getSigFigString(self.bins[this.current_r_bin].x1)}`);
            r_slider.select('text').attr('x', function(){return -(this.getBBox().width/2) + self.slider_width/2});

            
            this.model.state.metricUpdated = false;
        }
        
        /**
         * 
         * EXIT
         * 
         */
        
        bars.exit().remove();
        rev_bars.exit().remove();
    }

}

export default ScentedSliderPopup;