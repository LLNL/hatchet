import View from '../utils/view';
import {d3, globals} from './cct_globals';

class ScentedSliderPopup extends View{

    constructor(elem,model){
        super(elem, model);
        this.popup_dims = {
            'width': 300,
            'height': 150,
            'padding': 30
        }
        this.hist_height = this.popup_dims.height*.5;
        this.num_bins = 25;

        this._svg = d3.select(elem)
                        .append('svg')
                        .attr('width', this.popup_dims['width'])
                        .attr('height', this.popup_dims['height'])
                        .style('position', 'absolute')
                        .style('left', (this.elem.clientWidth*.5 - this.popup_dims.width*.5) + 'px')
                        // .style('visibility', 'hidden');

        this.bins = model.fetchBins(this.num_bins);
       
        this.update_bin_count_ranges();

        this.slider_range = model.forest.forestMetrics[model.state.primaryMetric];
        this.h_x_scale = d3.scaleLinear().domain([0,this.bins.length]).range([0, this.popup_dims['width']-2*this.popup_dims.padding]);
        this.h_y_scale = d3.scaleLinear().domain(this.bin_count_range).range([4, this.hist_height]);
        this.invert_y_scale = d3.scaleLinear().domain(this.bin_count_range).range([this.hist_height, 0]);

        this.pre_render();
        this.render();
    }
    
    update_bin_count_ranges(){
        this.bin_count_range = [Number.MAX_VALUE, Number.MIN_VALUE];

        this.bins.forEach(d=>{
            this.bin_count_range[0] = Math.min(d.length, this.bin_count_range[0]);
            this.bin_count_range[1] = Math.max(d.length, this.bin_count_range[1]);
        })
    }

    pre_render(){
        const self = this;

        //render histogram
        this._svg.append('rect')
                    .attr('height', this.popup_dims['height'])
                    .attr('width', this.popup_dims['width'])
                    .attr('fill', 'rgba(255,255,255,1)')
                    .attr('stroke', 'rgba(0,0,0,1)')
                    .attr('stroke-width', 2);
        
        this._svg.append('text')
                    .text('Brush Over Distribution to Set Filter Range')
                    .attr('fill', 'rgba(0,0,0,1)')
                    .attr('y', 20)
                    .attr('x', 20);
                    
        this._svg.append('g')
                    .attr('class', 'hist-grp')
                    .attr('height', this.hist_height)
                    .attr('width', this.popup_dims['width'])
                    .attr('transform', `translate(${this.popup_dims.padding}, ${this.popup_dims.padding+5})`);

        
        this.hist_grp = this._svg.select('.hist-grp');

        this.hist_grp.append('g')
                        .attr('class', 'left-axis')
                        .attr('transform', `translate(0, 0)`)
                        .call(d3.axisLeft(this.invert_y_scale).ticks(5));


        const slider_width = 10;
        const slider_height = 20;
        this.l_slider_pos = -(slider_width/2);
        this.r_slider_pos = this.popup_dims['width']-2*this.popup_dims.padding - (slider_width/2);

        let current_l_bin = parseInt(this.h_x_scale.invert(this.l_slider_pos));
        let current_r_bin = parseInt(this.h_x_scale.invert(this.r_slider_pos));

        let dragHandler = d3.drag()
                            .on("drag", function(){
                                if(d3.event.x > self.l_slider_pos && d3.event.x < self.r_slider_pos){
                                    d3.select(this)
                                        .attr('transform', `translate(${d3.event.x},0)`);
                                    d3.select(this).select('text').text(`${self.bins[parseInt(self.h_x_scale.invert(d3.event.x))].x1}`)
                                }else if (d3.event.x < self.l_slider_pos){
                                    d3.select(this)
                                        .attr('transform', `translate(${self.l_slider_pos},0)`)
                                }
                                else if (d3.event.x > self.r_slider_pos){
                                    d3.select(this)
                                        .attr('transform', `translate(${self.r_slider_pos},0)`)
                                }

                            });

        let l_slider = this.hist_grp.append('g')
                                .attr('class', 'l-slider-grp')
                                .attr('transform', `translate(${this.l_slider_pos},0)`);
                    
        l_slider.append('rect')
                        .attr('class', 'left-handle')
                        .attr('width', slider_width)
                        .attr('height', slider_height)
                        .attr('y', this.hist_height+2)
                        .attr('fill', 'rgba(200,50,50,1)')
                        .attr('stroke', 'rgba(0,0,0,1)');

        l_slider.append('line')
                    .attr('class', 'left-line')
                    .attr('x1', (slider_width/2))
                    .attr('x2', (slider_width/2))
                    .attr('y1', 0)
                    .attr('y2', this.hist_height+2)
                    .attr('stroke', 'rgba(200,50,50,1)');

        l_slider.append('text')
                .text(`${this.bins[parseInt(this.h_x_scale.invert(this.l_slider_pos))].x0}`)
                .attr('y', this.hist_height+2+slider_height+14);

        dragHandler(l_slider);

        let r_slider = this.hist_grp.append('g')
                                .attr('class', 'r-slider-grp')
                                .attr('transform', `translate(${this.r_slider_pos},0)`);
                
                    
        r_slider.append('rect')
                        .attr('class', 'right-handle')
                        .attr('width', slider_width)
                        .attr('height', slider_height)
                        .attr('y', this.hist_height+2)
                        .attr('fill', 'rgba(200,50,50,1)')
                        .attr('stroke', 'rgba(0,0,0,1)');

        r_slider.append('line')
                    .attr('class', 'right-line')
                    .attr('x1', (slider_width/2))
                    .attr('x2', (slider_width/2))
                    .attr('y1', 0)
                    .attr('y2', this.hist_height+2)
                    .attr('stroke', 'rgba(200,50,50,1)');

        r_slider.append('text')
                .text(`${this.bins[parseInt(this.h_x_scale.invert(this.r_slider_pos))].x1}`)
                .attr('y', this.hist_height+2+slider_height+14);

        dragHandler(r_slider);
    }

    render(){
        this.bins = this.model.fetchBins(this.num_bins);
        this.update_bin_count_ranges();

        this.h_y_scale.domain(this.bin_count_range);
        this.invert_y_scale.domain(this.bin_count_range);

        this.hist_grp.select('.left-axis')
                .transition()
                .duration(globals.duration)
                .call(d3.axisLeft(this.invert_y_scale).ticks(5));

        // this._svg.style('visibility', ()=>{
        //     if(this.model.state.pruneEnabled) return 'visible';
        //     return 'hidden';
        // });



        let bars = this.hist_grp.selectAll('.hist-bar')
        .data(this.bins);

        bars.enter()
            .append('rect')
            .attr('class', 'hist-bar')
            .attr('width', (this.popup_dims['width']-this.popup_dims.padding*2)/this.bins.length)
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
            .attr('fill', 'rgba(200,200,200,1')
            .attr('stroke','rgba(0,0,0,1)')
            .attr('stroke-width', '1px');

        //update bars
        bars.transition()
            .duration(750)
            .attr('height', d => {
                if(d.length != 0){
                    return this.h_y_scale(d.length);
                } 
                return 0;
            })
            .attr('y', (d)=>{
                if(d.length != 0){
                    return (this.hist_height-this.h_y_scale(d.length)) //- v_bar_negative_padding;
                }
                return this.hist_height;
            });


    }

}

export default ScentedSliderPopup;