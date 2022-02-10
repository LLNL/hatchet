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
            .style('max-width','400px')
            .style('max-height', '200px')
            .style('overflow', 'scroll')
            .html('<p>Click a node or "Select nodes" to see more info</p>');

    }

    render(){
        this.tooltip.html(this.model.data["tipText"]);
    }

}

export default TooltipView;