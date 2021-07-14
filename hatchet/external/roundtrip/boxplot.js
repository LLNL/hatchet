// TODO: Adopt MVC pattern for this module.
(function (element) {
    const BOXPLOT_TYPES = ["tgt", "bkg"];
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
    function cleanInputs(strings) {
        return strings.map((_) => _.replace(/'/g, '"'));
    }

    /**
     * Sort the callsite ordering based on the attribute.
     *
     * @param {Array} callsites - Callsites as a list.
     * @param {Stirng} metric - Metric (e.g., time or time (inc)).
     * @param {String} attribute - Attribute to sort by.
     * @param {String} boxplotType -  boxplot type - for options, refer BOXPLOT_TYPES.
     */
    function sortByAttribute(callsites, metric, attribute, sortOrder, boxplotType) {
        const SORT_MULTIPLIER = {
            "inc": -1,
            "desc": 1
        }

        if (!BOXPLOT_TYPES.includes(boxplotType)) {
            console.error("Invalid boxplot type. Use either 'tgt' or 'bkg'")
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
            "sortOrders": ["desc", "inc"],
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
        visualize(data);

        // --------------------------------------------------------------------------------
        // Visualization functions.
        // --------------------------------------------------------------------------------
        function _format(d) {
            return {
                "min": d3_utils.formatRuntime(d.min),
                "max": d3_utils.formatRuntime(d.max),
                "mean": d3_utils.formatRuntime(d.mean),
                "var": d3_utils.formatRuntime(d.var),
                "imb": d3_utils.formatRuntime(d.imb),
                "kurt": d3_utils.formatRuntime(d.kurt),
                "skew": d3_utils.formatRuntime(d.skew),
            };
        }

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
                state.selectedSortOrder = d.target.value;
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

        function visualizeStats(g, d, type, boxWidth) {
            const stats = _format(d);
            const TYPE_TEXTS = {
                "tgt": "Target",
                "bkg": "Background"
            };

            // Text fpr statistics title.
            const xOffset = type === "tgt" ? 1.1 * boxWidth : 1.4 * boxWidth;
            const textColor = type === "tgt" ? "#4DAF4A" : "#202020";

            const statsG = g.append("g")
                .attr("class", "stats");

            d3_utils.drawText(statsG, TYPE_TEXTS[type], xOffset, 15, 0, textColor, "underline");

            // Text for statistics
            let statIdx = 1;
            for (let [stat, val] of Object.entries(stats)) {
                d3_utils.drawText(statsG, `${stat}:  ${val}`, xOffset, 15, statIdx, textColor);
                statIdx += 1;
            }
        }

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
            for (let idx = 0; idx < d.outliers["values"].length; idx += 1) {
                outliers.push({
                    x: xScale(d.outliers["values"][idx]),
                    value: d.outliers["values"][idx],
                    rank: d.outliers["ranks"][idx],
                    y: 10
                });
            }
            d3_utils.drawCircle(boxG, outliers, outlierRadius, fillColor[type]);
        }

        function visualize(data) {
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
            }
        }

        function reset() {
            d3_utils.clearSvg(globals.id);
            visualize(data);
        }
    });
})(element);