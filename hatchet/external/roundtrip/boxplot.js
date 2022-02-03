// TODO: Adopt MVC pattern for this module.
(function (element) {
    const BOXPLOT_TYPES = ["tgt", "bkg"];
    const SORTORDER_TYPES = ["asc", "desc"];
    const [path, visType, variableString] = cleanInputs(argList);

    // Quit if visType is not boxplot. 
    if (visType !== "boxplot") {
        console.error("Incorrect visualization type passed.")
        return;
    }

    // --------------------------------------------------------------------------------
    // RequireJS setup.
    // --------------------------------------------------------------------------------
    // Setup the requireJS config to get required libraries.
    requirejs.config({
        baseUrl: path,
        paths: {
            d3src: 'https://d3js.org',
            lib: 'lib',
        },
        map: {
            '*': {
                'd3': 'd3src/d3.v6.min',
                'd3-utils': 'lib/d3_utils',
            }
        }
    });

    // --------------------------------------------------------------------------------
    // Utility functions.
    // --------------------------------------------------------------------------------
    // TODO: Move this to a common utils folder.
    /**
     * Utility to remove single quotes.
     * 
     * @param {String} strings strings with single quotes.
     * @returns {String} strings without single quotes.
     */
    function cleanInputs(strings) {
        return strings.map((_) => _.replace(/'/g, '"'));
    }

    /**
     * Sort the callsite ordering based on the attribute.
     *
     * @param {Array} callsites - Callsites as a list.
     * @param {String} metric - Metric passed by user (e.g., time or time (inc)).
     * @param {String} attribute - Attribute to sort by.
     * @param {String} sortOrder - Sorting order - for options, refer SORTORDER_TYPES.
     * @param {String} boxplotType - boxplot type - for options, refer BOXPLOT_TYPES.
     */
    function sortByAttribute(callsites, metric, attribute, sortOrder, boxplotType) {
        const SORT_MULTIPLIER = {
            "asc": -1,
            "desc": 1
        }

        if (!SORTORDER_TYPES.includes(sortOrder)) {
            console.error("Invalid sortOrder. Use either 'asc' or 'desc'");
        }

        if (!BOXPLOT_TYPES.includes(boxplotType)) {
            console.error("Invalid boxplot type. Use either 'tgt' or 'bkg'");
        }

        // Sanity check to see if the boxplotType (i.e., "tgt", "bkg") is present in the callsites.
        let _is_empty = false;
        Object.keys(callsites).map(function (key) {
            if (callsites[key][boxplotType] === undefined) {
                _is_empty = true;
            }
        })

        let items = Object.keys(callsites).map(function (key) {
            return [key, callsites[key][boxplotType]];
        });

        if (!_is_empty) {
            items = items.sort((first, second) => {
                return SORT_MULTIPLIER[sortOrder] * (second[1][metric][attribute] - first[1][metric][attribute]);
            });
        }

        return items.reduce(function (map, obj) {
            if (obj[1] !== undefined) {
                map[obj[0]] = obj[1][metric];
            } else {
                map[obj[0]] = obj[1];
            }
            return map;
        }, {});
    }

    require(['d3', 'd3-utils'], (d3, d3_utils) => {
        // --------------------------------------------------------------------------------
        // Main logic.
        // --------------------------------------------------------------------------------
        const data = JSON.parse(variableString);
        const callsites = Object.keys(data);

        // We add a random number to avoid deleting an existing boxplot in the
        // jupyter cell.
        // TODO: use the parent's id instead of random number.
        const globals = Object.freeze({
            "id": "boxplot-vis-" + Math.ceil(Math.random() * 100), 
            "attributes": ["mean", "min", "max", "var", "imb", "kurt", "skew"],
            "sortOrders": ["desc", "asc"],
            "topNCallsites": [5, 10, 25, 100, "all"],
            "tickCount": 5,
            "boxContainerHeight": 200,
        })

        // State for the module.
        const state = {
            selectedMetric: null,
            selectedAttribute: null,
            selectedSortOrder: 'desc',
            selectedTopNCallsites: 5,
        };
        
        menu(data);
        const variance_dict = visualize(data);
        variance_df = "'" + dict_to_csv(variance_dict, "tgt") + "'";

        // --------------------------------------------------------------------------------
        // Visualization functions.
        // --------------------------------------------------------------------------------
        /**
         * Format the statistics runtime. We use the mantessa and exponent
         * format. For more info, refer d3_utils.formatRuntime.
         * 
         * @param {Object} d Statistics object
         * @returns {Object} Formatted statistics object.
         */
        function _format(d) {
            return {
                "min": d3_utils.formatRuntime(d.min),
                "max": d3_utils.formatRuntime(d.max),
                "mean": d3_utils.formatRuntime(d.mean),
                "var": d3_utils.formatRuntime(d.var),
                "imb": d3_utils.formatRuntime(d.imb),
                "kurt": d3_utils.formatRuntime(d.kurt),
                "skew": d3_utils.formatRuntime(d.skew)
            };
        }

        /**
         * Convert the stats dictionary to a csv.
         * 
         * @param {Object} dict Statistics Object
         * @param {Object} boxplotType - boxplot type - for options, refer BOXPLOT_TYPES.
         * @return {String} result dictionary reformatted as a string (csv format)
         */
        function dict_to_csv(dict, boxplotType) {
            const callsites = Object.keys(dict);
            const stat_columns = ["min", "max", "mean", "var", "imb", "kurt", "skew"]
            let string = 'name,' + stat_columns.join(",") + ";";

            for (let callsite of callsites){
                const d = dict[callsite][boxplotType];

                let statsString = `${callsite},`;
                for (let stat of stat_columns) {
                    if (Object.keys(d).includes(stat)) {
                        statsString += d[stat] + ",";
                    }
                }
                string += statsString.substring(0, statsString.length - 1) +  ";";
            }

            const result = string.substring(0, string.length - 1)

            // Assertions to check if the right number of columns are being
            // passed.
            for (let str of result.split(";")) {
                if (str.split(",").length !== stat_columns.length + 1){
                    console.error("Mismatch in the number of stats metrics and data");
                    console.debug("Columns: ", result.split(";")[0]);
                    console.debug("Data: ", str);
                }
            }
            
            return result;
        }

        /**
         * Renders menu view for selecting metric, attribute, sortOrder and
         * callsites.
         * 
         * @param {Object} data 
         */
        function menu(data) {
            // Selection dropdown for metrics.
            const metrics = Object.keys(data[callsites[0]]["tgt"]);
            if (state.selectedMetric == null) state.selectedMetric = metrics[0]
            const metricSelectTitle = "Metric: ";
            const metricSelectId = "metricSelect";
            const metricOnChange = (d) => { 
                state.selectedMetric = d.target.value; 
                reset();
            };
            d3_utils.selectionDropDown(element, metrics, metricSelectId, metricSelectTitle, metricOnChange);

            // Selection dropdown for attributes.
            if (state.selectedAttribute == null) state.selectedAttribute = globals.attributes[0];
            const attributeSelectTitle = "Sort by: ";
            const attributeSelectId = "attributeSelect";
            const attributeOnChange = (d) => { 
                state.selectedAttribute = d.target.value;
                reset();
            };
            d3_utils.selectionDropDown(element, globals.attributes, attributeSelectId, attributeSelectTitle, attributeOnChange);
            
            // Selection dropdown for sortOrder.
            const sortOrderSelectTitle = "Sort order: ";
            const sortOrderSelectId = "sortingSelect";
            const sortOrderOnChange = (d) => { 
                state.selectedSortOrder = d.target.value;
                reset();
            };
            d3_utils.selectionDropDown(element, globals.sortOrders, sortOrderSelectId, sortOrderSelectTitle, sortOrderOnChange);

            // Selection dropdown for topNCallsites.
            const topNCallsitesSelectTitle = "Top N callsites: ";
            const topNCallsitesSelectId = "topNCallsitesSelect";
            const topNCallsitesOnChange = (d) => { 
                state.selectedTopNCallsites = d.target.value;
                reset();
            };
            d3_utils.selectionDropDown(element, globals.topNCallsites, topNCallsitesSelectId, topNCallsitesSelectTitle, topNCallsitesOnChange);
        }

        /**
         * Renders the statistics as rows.
         * 
         * @param {svg.g} g HTML element.
         * @param {Object} d Data 
         * @param {String} boxplotType boxplot type - for options, refer BOXPLOT_TYPES.
         * @param {Number} boxWidth Width of the boxplot view.
         * 
         * d - format : {"tgt": stats, "bkg": stats }
         */
        function visualizeStats(g, d, boxplotType, boxWidth) {
            const stats = _format(d);
            const TYPE_TEXTS = {
                "tgt": "Target",
                "bkg": "Background"
            };

            // Text fpr statistics title.
            const xOffset = boxplotType === "tgt" ? 1.1 * boxWidth : 1.4 * boxWidth;
            const textColor = boxplotType === "tgt" ? "#4DAF4A" : "#202020";

            const statsG = g.append("g")
                .attr("class", "stats");

            d3_utils.drawText(statsG, TYPE_TEXTS[boxplotType], xOffset, 15, 0, textColor, "underline");

            // Text for statistics
            let statIdx = 1;
            for (let [stat, val] of Object.entries(stats)) {
                d3_utils.drawText(statsG, `${stat}:  ${val}`, xOffset, 15, statIdx, textColor);
                statIdx += 1;
            }
        }

        /**
         * Renders boxplots for the callsites.
         * 
         * @param {svg.g} g HTML element.
         * @param {Object} d Data
         * @param {String} boxplotType boxplot type - for options, refer BOXPLOT_TYPES.
         * @param {d3.scale} xScale Scale for layouting the boxplot.
         * @param {Boolean} drawCenterLine draws center line, if true.
         */
        function visualizeBoxplot(g, d, type, xScale, drawCenterLine) {
            const fillColor = {
                "tgt": "#4DAF4A",
                "bkg": "#D9D9D9"
            };
            const strokeWidth = 1;
            const boxYOffset = 30;
            const strokeColor = "#202020";
            const boxHeight = 80;

            const boxG = g.append("g").attr("class", "box");

            // Centerline
            if (drawCenterLine) {
                const [min, max] = xScale.domain();
                d3_utils.drawLine(boxG, xScale(min), boxYOffset + boxHeight / 2, xScale(max), boxYOffset + boxHeight / 2, strokeColor);
            }

            // Tooltip
            const tooltipWidth = 100;
            const tooltipHeight = 30;
            const tooltipText = `q1: ${d3_utils.formatRuntime(d.q[1])}, q3: ${d3_utils.formatRuntime(d.q[3])}`;
            const mouseover = (event) => d3_utils.drawToolTip(boxG, event, tooltipText, tooltipWidth, tooltipHeight);
            const mouseout = (event) => d3_utils.clearToolTip(boxG, event);
            const click = (event) => d3_utils.drawToolTip(boxG, event, tooltipText, tooltipWidth, tooltipHeight);

            // Box
            d3_utils.drawRect(boxG, {
                "class": "rect",
                "x": xScale(d.q[1]),
                "y": boxYOffset,
                "height": boxHeight,
                "fill": fillColor[type],
                "width": xScale(d.q[3]) - xScale(d.q[1]),
                "stroke": strokeColor,
                "stroke-width": strokeWidth
            }, click, mouseover, mouseout);

            // Markers
            const markerStrokeWidth = 3;
            d3_utils.drawLine(boxG, xScale(d.q[0]), boxYOffset, xScale(d.q[0]), boxYOffset + boxHeight, fillColor[type], markerStrokeWidth);
            d3_utils.drawLine(boxG, xScale(d.q[4]), boxYOffset, xScale(d.q[4]), boxYOffset + boxHeight, fillColor[type], markerStrokeWidth);

            // Outliers
            const outlierRadius = 4;
            let outliers = [];
            for (let idx = 0; idx < d.ometric.length; idx += 1) {
                outliers.push({
                    x: xScale(d.ometric[idx]),
                    value: d.ometric[idx],
                    // rank: d.outliers["ranks"][idx],
                    y: 10
                });
            }
            d3_utils.drawCircle(boxG, outliers, outlierRadius, fillColor[type]);
        }

        /**
         * Renders the vis for the provided callsites object. 
         * 
         * @param {Object} data 
         * @returns {Object} variance_dict = { "tgt": stats, "bkg": stats }
         * 
         * data = {
         *  "callsite_name": {
         *      "tgt": {
         *          "metric1": stats,
         *          "metric2": stats,
         *      },
         *      "bkg": {
         *          "metric1": stats,
         *          "metric2": stats,
         *      }
         *  }
         * }
         * 
         * stats = {
         *  "min": {float},
         *  "max": {float},
         *  "mean": {float},
         *  "imb": {float},
         *  "kurt": {float},
         *  "skew": {float},
         *  "q": {Array} = [q0, q1, q2, q3, q4],
         *  "outliers": {Object} = {
         *      "values": {Array},
         *      "keys": {Array}
         *  }
         * }
         */
        function visualize(data) {
            const variance_dict = {}

            const { selectedAttribute, selectedMetric, selectedSortOrder, selectedTopNCallsites } = state;
            console.debug(`Selected metric: ${selectedAttribute}`);
            console.debug(`Selected Attribute: ${selectedMetric}`);
            console.debug(`Selected SortOrder: ${selectedSortOrder}`)
            console.debug(`Selected Top N callsites: ${selectedTopNCallsites}`)

            // Sort the callsites by the selected attribute and metric.
            const tgtCallsites = sortByAttribute(data, selectedMetric, selectedAttribute, selectedSortOrder, "tgt");
            const bkgCallsites = sortByAttribute(data, selectedMetric, selectedAttribute, selectedSortOrder, "bkg");
            
            const callsites = [...new Set([...Object.keys(tgtCallsites), ...Object.keys(bkgCallsites)])];
            
            let topNCallsites = callsites;
            if(selectedTopNCallsites !== "all" && selectedTopNCallsites < callsites.length) {
                topNCallsites = callsites.slice(0, selectedTopNCallsites);
            }

            // Assign an index to the callsites. 
            const idxToNameMap = Object.assign({}, topNCallsites.map((callsite) => (callsite)));
            const nameToIdxMap = Object.entries(idxToNameMap).reduce((acc, [key, value]) => (acc[value] = key, acc), {});

            // Setup VIS area.
            const margin = { top: 30, right: 0, bottom: 0, left: 0 },
                containerHeight = globals.boxContainerHeight * Object.keys(topNCallsites).length + 2 * margin.top,
                width = element.clientWidth - margin.right - margin.left,
                height = containerHeight - margin.top - margin.bottom;
            const svgArea = d3_utils.prepareSvgArea(width, height, margin, globals.id);
            const svg = d3_utils.prepareSvg(element, svgArea);

            d3_utils.drawText(svg, "Total number of callsites: " + callsites.length, 0, 0, 0, "#000", "underline");

            const boxWidth = 0.6 * width;
            for (let callsite of topNCallsites) {
                let tgt = null;
                if (callsite in tgtCallsites) tgt = tgtCallsites[callsite];

                let bkg = null;
                if (callsite in bkgCallsites) bkg = bkgCallsites[callsite];

                // Set the min and max for xScale.
                let min = 0, max = 0;
                if (bkg === undefined) {
                    min = tgt.min;
                    max = tgt.max;
                } else {
                    min = Math.min(tgt.min, bkg.min);
                    max = Math.max(tgt.max, bkg.max);
                }
                const xScale = d3.scaleLinear()
                    .domain([min, max])
                    .range([0.05 * boxWidth, boxWidth - 0.05 * boxWidth]);

                // Set up a g container
                const idx = nameToIdxMap[callsite];
                const gId = "box-" + idx;
                const gYOffset = 200;
                const g = svg.append("g")
                    .attr("id", gId)
                    .attr("width", boxWidth)
                    .attr("transform", "translate(0, " + ((gYOffset * idx) + 30) + ")");

                const axisOffset = gYOffset * 0.6;
                d3_utils.drawXAxis(g, xScale, globals.tickCount, d3_utils.formatRuntime, 0, axisOffset, "black");

                // Text for callsite name.
                const callsiteIndex = parseInt(idx) + 1
                d3_utils.drawText(g, `(${callsiteIndex}) Callsite : ` + callsite, 0, 0, 0, "#000");

                visualizeStats(g, tgt, "tgt", boxWidth);
                if (bkg !== undefined) {
                    visualizeStats(g, bkg, "bkg", boxWidth);
                }

                visualizeBoxplot(g, tgt, "tgt", xScale, true);
                if (bkg !== undefined) {
                    visualizeBoxplot(g, bkg, "bkg", xScale, false);
                }

                variance_dict[callsite] = { tgt, bkg };
            }

            return variance_dict
        }

        /**
         * Clears the view and resets the view. 
         * 
         */
        function reset() {
            d3_utils.clearSvg(globals.id);
            const variance_dict = visualize(data);
            variance_df = "'" + dict_to_csv(variance_dict, "tgt") + "'"; 
        }
    });
})(element);