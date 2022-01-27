
const makeColorManager = function(model) {
    // TODO: Move the colors to a color.js.
    const REGULAR_COLORS = [
        ['#006d2c', '#31a354', '#74c476', '#a1d99b', '#c7e9c0', '#edf8e9'], //green
        ['#a50f15', '#de2d26', '#fb6a4a', '#fc9272', '#fcbba1', '#fee5d9'], //red
        ['#08519c', '#3182bd', '#6baed6', '#9ecae1', '#c6dbef', '#eff3ff'], //blue
        ['#54278f', '#756bb1', '#9e9ac8', '#bcbddc', '#dadaeb', '#f2f0f7'], //purple
        ['#a63603', '#e6550d', '#fd8d3c', '#fdae6b', '#fdd0a2', '#feedde'], //orange
        ['#252525', '#636363', '#969696', '#bdbdbd', '#d9d9d9', '#f7f7f7']
    ];

    const CAT_COLORS = ["#3366cc", "#dc3912", "#ff9900", "#109618", "#990099", "#0099c6", "#dd4477", "#66aa00", "#b82e2e", "#316395", "#994499", "#22aa99", "#aaaa11", "#6633cc", "#e67300", "#8b0707", "#651067", "#329262", "#5574a6", "#3b3eac"];

    const _regularColors = {
        0: REGULAR_COLORS,
        1: REGULAR_COLORS.map((colorArr) => [].concat(colorArr).reverse()),
        2: CAT_COLORS,
        3: [].concat(CAT_COLORS).reverse()
    };

    const ALL_COLORS = ['#d73027', '#fc8d59', '#fee090', '#e0f3f8', '#91bfdb', '#4575b4'];

    const _allTreesColors = {
        0: ALL_COLORS,
        1: [].concat(ALL_COLORS).reverse(),
        2: CAT_COLORS,
        3: [].concat(CAT_COLORS).reverse(),
    };

    const _state = model.state;
    const _forestMinMax = model.forest.forestMinMax;
    const _forestStats = model.forest.forestMetrics;
    const _metricColumns = model.forest.metricColumns;
    const _attributeColumns = model.forest.attributeColumns;

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

                // Calculate the range of min/max.
                const metricRange = _d.max - _d.min;

                // Set colorMap for runtime metrics.
                let proportion_of_total = nodeMetric / 1;

                // If min != max, we can split the runtime into bins.
                if (metricRange != 0) {
                    proportion_of_total = (nodeMetric - _d.min) / metricRange;
                }

                // TODO: Generalize to any bin size.
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
}

export default makeColorManager;