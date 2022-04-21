import { d3 } from './cct_globals';


class ColorManager{
    /**
     * Class that manages the color schemes used for legends
     * and coloring the nodes of the tree.
     * @param {Model} model 
     * @param {int} treeIndex 
     */
    constructor(model, treeIndex){
        const REGULAR_COLORS = [
            ['#006d2c', '#31a354', '#74c476', '#a1d99b', '#c7e9c0', '#edf8e9'], //green
            ['#a50f15', '#de2d26', '#fb6a4a', '#fc9272', '#fcbba1', '#fee5d9'], //red
            ['#08519c', '#3182bd', '#6baed6', '#9ecae1', '#c6dbef', '#eff3ff'], //blue
            ['#54278f', '#756bb1', '#9e9ac8', '#bcbddc', '#dadaeb', '#f2f0f7'], //purple
            ['#a63603', '#e6550d', '#fd8d3c', '#fdae6b', '#fdd0a2', '#feedde'], //orange
            ['#252525', '#636363', '#969696', '#bdbdbd', '#d9d9d9', '#f7f7f7']
        ];
    
        const CAT_COLORS = ["#3366cc", "#dc3912", "#ff9900", "#109618", "#990099", "#0099c6", "#dd4477", "#66aa00", "#b82e2e", "#316395", "#994499", "#22aa99", "#aaaa11", "#6633cc", "#e67300", "#8b0707", "#651067", "#329262", "#5574a6", "#3b3eac"];
    
        this._regularColors = {
            0: REGULAR_COLORS.map((colorArr) => [].concat(colorArr).reverse()),
            1: REGULAR_COLORS,
            2: CAT_COLORS,
            3: [].concat(CAT_COLORS).reverse()
        };
    
        const ALL_COLORS = ['#d73027', '#fc8d59', '#fee090', '#e0f3f8', '#91bfdb', '#4575b4'];
    
        this._allTreesColors = {
            0: [].concat(ALL_COLORS).reverse(),
            1: ALL_COLORS,
            2: CAT_COLORS,
            3: [].concat(CAT_COLORS).reverse(),
        };
        
        this._model = model;
        this._state = model.state;
        this._forestMinMax = model.forest.forestMinMax;
        this._forestStats = model.forest.forestMetrics;
        this._metricColumns = model.forest.metricColumns;
        this._attributeColumns = model.forest.attributeColumns;
        this._aggregateMinMax = model.forest.aggregateMinMax;

        this.treeIndex = treeIndex;
        this.cachedPrimaryMetric = this._state.primaryMetric;
        this.cachedColorScheme = this._state.colorScheme;

        this.universal_color_scale = d3.scaleQuantize()
                                .domain([this._forestMinMax[this._state.primaryMetric].min,this._forestMinMax[this._state.primaryMetric].max])
                                .range(this._allTreesColors[this._state.colorScheme]);

        this.single_color_scale = d3.scaleQuantize()
                                    .domain([this._forestStats[this.treeIndex][this._state.primaryMetric].min, this._forestStats[this.treeIndex][this._state.primaryMetric].max])
                                    .range(this._regularColors[this._state.colorScheme][this.treeIndex]);

        this.agg_color_scale = d3.scaleQuantize()
                                .domain([this._aggregateMinMax[this._state.primaryMetric].min, this._aggregateMinMax[this._state.primaryMetric].max])
                                .range(this._allTreesColors[this._state.colorScheme]);

    }

    _updateScales(){
        /**
         * Updates the scales to reflect new data
         *  when the primary metric changes.
         */

        const a_dom = this._aggregateMinMax[this._state.primaryMetric];
        this.agg_color_scale.domain([a_dom.min,a_dom.max]);

        if(this._state.primaryMetric != this.cachedPrimaryMetric){
            const u_dom = this._forestMinMax[this._state.primaryMetric];
            const s_dom = this._forestStats[this.treeIndex][this._state.primaryMetric];

            this.universal_color_scale.domain([u_dom.min,u_dom.max]);
            this.single_color_scale.domain([s_dom.min,s_dom.max]);
            this.cachedPrimaryMetric = this._state.primaryMetric;
        }
        if(this._state.colorScheme != this.cachedColorScheme){
            this.universal_color_scale.range(this._allTreesColors[this._state.colorScheme]);
            this.single_color_scale.range(this._regularColors[this._state.colorScheme][this.treeIndex]);
            this.agg_color_scale.range(this._allTreesColors[this._state.colorScheme]);
            this.cachedColorScheme = this._state.primaryMetric;
        }
    }

    _getDomainFromScale(scale){
        /**
         * Returns an array of ranges from a 
         * d3.scaleQuantize
         */
        let ranges = []
        for(let col of scale.range()){
            ranges.push(scale.invertExtent(col));
        }

        ranges[0][0] = Math.min(ranges[0][0], this._aggregateMinMax[this._state.primaryMetric].min);
        ranges[ranges.length-1][1] = Math.max(ranges[ranges.length-1][1], this._aggregateMinMax[this._state.primaryMetric].max);

        return ranges;
    }

    _getCorrectScale(){
        /**
         * Returns color scale based on the state of
         *  the color scheme: universal or unique to each
         *  tree in the forest.
         */
        if(this._model.data["legends"][this._state["legend"]].includes("Unified")){
            return this.universal_color_scale;
        }
        else{
            return this.single_color_scale;
        }
    }

    getAggLegendDomains(){
        /**
         * Returns domains across aggregate nodes.
         */
        this._updateScales();
        return this._getDomainFromScale(this.agg_color_scale);
    }

    getLegendDomains(){
        /**
         * Returns domains across all normal nodes.
         */
        this._updateScales();
        
        return this._getDomainFromScale(this._getCorrectScale());
    }

    calcColorScale(nodeData){
        /**
         * Update the scales for the current primary metric.
         */
        this._updateScales();
        const nodeMetric = nodeData.metrics[this._state.primaryMetric];
        return this._getCorrectScale()(nodeMetric);
    }

    calcAggColorScale(nodeData){
         /**
         * Update aggregate scales for the current primary metric.
         */
        this._updateScales();
        const nodeMetric = nodeData.aggregateMetrics[this._state.primaryMetric];
        return this._getCorrectScale()(nodeMetric);
    }

    getColorLegend(){
        this._updateScales();

        return this._getCorrectScale().range();
    }

    getAggColorLegend(){
        this._updateScales();
        return this.agg_color_scale.range();
    }

}


const makeColorManager = function(model) {
    // TODO: Move the colors to a color.js.
   


    let color_scale = d3.scaleQuantize();

    return {
        setColors: function(treeIndex) {
            const curMetric = _state["primaryMetric"];
            const colorScheme = _state["colorScheme"];

            if (_metricColumns.includes(curMetric)) {
                if (treeIndex == -1) return _allTreesColors[colorScheme];
                else return _regularColors[colorScheme][treeIndex % REGULAR_COLORS.length];
            } else if (_attributeColumns.includes(curMetric)) {
                if (treeIndex == -1) return _allTreesColors[2 + colorScheme];
                else return _regularColors[2 + colorScheme];
            }
        },
        getLegendDomains: function(treeIndex){
            /**
             * Sets the min and max of the legend. 
             * 
             * @param {Int} treeIndex - The index of the current tree's legend being set
             */

            const curMetric = _state["primaryMetric"];

            // so hacky: need to fix later
            if (model.data["legends"][_state["legend"]].includes("Unified")) {
                treeIndex = -1;
            }

            let metricMinMax;
            if (treeIndex === -1) { //unified color legend
                metricMinMax = _forestMinMax[curMetric]
            } else { // individual color legend
                metricMinMax = _forestStats[treeIndex][curMetric]
            }


            let colorScaleDomain;
            if (_metricColumns.includes(curMetric)) {
                let metricRange = metricMinMax.max - metricMinMax.min;
                colorScaleDomain = [0, 0.1, 0.3, 0.5, 0.7, 0.9, 1].map(function(x) {
                    return x * metricRange + metricMinMax.min;
                });
            } else if (_attributeColumns.includes(curMetric)) {
                colorScaleDomain = metricMinMax;
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

            return this.setColors(treeIndex);
        },
        calcColorScale: function(nodeData, treeIndex) {
            /**
             * Calculates the bins for the color scheme based on the current, user-selected metric.
             *
             * @param {String} nodeData - the name of the current metric being mapped to a color range
             */
            // Decide the color scheme for the settings.
            const colorSchemeUsed = this.setColors(treeIndex);
            const curMetric = _state["primaryMetric"];

            // Get the suitable data based on the Legend settings.
            let _d;
            if (treeIndex === -1) {
                _d = _forestMinMax[curMetric];
            } else {
                _d = _forestStats[treeIndex][curMetric];
            }

            if (_attributeColumns.includes(curMetric)) {
                const nodeMetric = nodeData.attributes[curMetric];
                const indexOfMetric = _d.indexOf(nodeMetric);
                return colorSchemeUsed[indexOfMetric];
            } else if (_metricColumns.includes(curMetric)) {
                const nodeMetric = nodeData.metrics[curMetric];
                color_scale.domain([_d.min, _d.max]).range(colorSchemeUsed);
                return color_scale(nodeMetric);
            }
        }
    }
}

export default ColorManager;