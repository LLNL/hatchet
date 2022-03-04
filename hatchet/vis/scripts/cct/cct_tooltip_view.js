import { d3 } from "./cct_globals";
import View from "../utils/view";

class TooltipView extends View {
    /**
     * Class that instantiates the view for the tooltip that appears with selected nodes.
     * 
     * @param {DOM Element} elem - The current cell of the calling Jupyter notebook
     * @param {Model} model - The model object containg data for the view
     */
    constructor(elem, model){
        super(elem, model);

        this.tooltip = d3.select(elem).append("div")
            .attr('id', 'tooltip')
            .style('position', 'absolute')
            .style('top', '50px')
            .style('right', '15px')
            .style('padding', '5px')
            .style('border-radius', '5px')
            .style('background', '#ccc')
            .style('color', 'black')
            .style('font-size', '14px')
            .style('font-family', 'monospace')
            .style('max-width','800px')
            .style('max-height', '200px')
            .style('overflow', 'scroll')
            .html('<p>Click a node or "Select nodes" to see more info</p>');

        d3.select('#site')
            .on(`scroll.${d3.select(elem).select('script').attr('id')}`, (e)=>{
                // console.log(d3.select(elem).select('script').attr('id'));
                if(this.elem.getBoundingClientRect().top < 150 && !( -this.elem.getBoundingClientRect().top - this.elem.getBoundingClientRect().height > -250) ){
                    this.tooltip
                        .style('position', 'fixed')
                        .style('top','150px');
                }
                else{
                    this.tooltip
                        .style('position', 'absolute')
                        .style('top', '50px')
                }
            })

    }

    render(){
        this.tooltip.html(this.model.data["tipText"]);
    }

}

export default TooltipView;