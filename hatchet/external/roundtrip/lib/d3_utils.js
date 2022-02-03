define(function (require) {
  const d3 = require("d3");

  return {
    calcContainerWidth: name => +d3.select(name).style('width').slice(0, -2),
    calcContainerHeight: name => +d3.select(name).style('height').slice(0, -2),
    calcCellWidth: (width, colNames) => width / colNames.length,
    calcCellHeight: (height, rowNames) => height / rowNames.length,
    calcCellSize: (width, height, colNames, rowNames, widthMax, heightMax) => [Math.min(calcCellWidth(width, colNames), widthMax), Math.min(calcCellHeight(height, rowNames), heightMax)],

    // SVG init.
    prepareSvgArea: (windowWidth, windowHeight, margin, id) => {
      return {
        width: windowWidth - margin.left - margin.right,
        height: windowHeight - margin.top - margin.bottom,
        margin: margin,
        id: id
      }
    },
    prepareSvg: (id, svgArea) => {
      const svg = d3.select(id)
        .append('svg')
        .attr("id", svgArea.id)
        .attr('width', svgArea.width + svgArea.margin.left + svgArea.margin.right)
        .attr('height', svgArea.height + svgArea.margin.top + svgArea.margin.bottom)
        .append('g')
        .attr('transform',
          'translate(' + svgArea.margin.left + ',' + svgArea.margin.top + ')');

      return svg;
    },
    clearSvg: (id) => {
      d3.selectAll("#" + id).remove();
    },
    initSvgInfo: (targetView, margin) => {
      const sd = targetView.svgData;
      const domId = targetView.domId;

      sd.svgArea = prepareSvgArea(
        calcContainerWidth(`#${domId}`),
        calcContainerHeight(`#${domId}`), margin || {
          top: 0,
          right: 0,
          bottom: 0,
          left: 0
        })
      sd.svg = prepareSvg(`#${domId}`, sd.svgArea);
      sd.domId = targetView.domId;
    },

    // Axes, Scaling
    genX: (data, svgArea, domain = null, scaler = d3.scaleLinear()) => {
      if (domain === null) {
        domain = d3.extent(data);
      }
      return scaler.domain(domain).range([0, svgArea.width]);
    },
    genInvX: (data, svgArea, domain = null, scaler = d3.scaleLinear()) => {
      if (domain === null) {
        domain = d3.extent(data);
      }
      return scaler.domain([0, svgArea.width]).range(domain);
    },
    genY: (data, svgArea, domain = null, scaler = d3.scaleLinear(), goUp = true) => {
      if (domain === null) {
        domain = d3.extent(data);
      }
      return goUp ?
        scaler.domain(domain).range([svgArea.height, 0]) :
        scaler.domain(domain).range([0, svgArea.height]);
    },
    genInvY: (data, svgArea, domain = null, scaler = d3.scaleLinear()) => {
      if (domain === null) {
        domain = d3.extent(data);
      }
      return scaler.domain([svgArea.height, 0]).range(domain);
    },

    // UI Components
    selectionDropDown: (element, data, id, title, onChange) => {
      d3.select(element).append('label').attr('for', id).text(title);
      const dropdown = d3.select(element).append("select")
        .attr("id", id)
        .style("margin", "10px 10px 10px 0px")
        .on('change', onChange);

      const options = dropdown.selectAll('option')
        .data(data)
        .enter()
        .append('option');

      options.text(d => d)
        .attr('value', d => d);
    },


    // Formatting numbers
    formatRuntime: (val) => {
      if (val == 0) {
        return val;
      }
      let format = d3.format(".3");
      return format(val);
    },

    // SVG elements
    drawRect: (element, attrDict, click = () => { }, mouseover = () => { }, mouseout = () => { }) => {
      return element.append("rect")
        .attr("x", attrDict["x"])
        .attr("y", attrDict["y"])
        .attr("height", attrDict["height"])
        .attr("width", attrDict["width"])
        .attr("fill", attrDict["fill"])
        .attr("stroke", attrDict["stroke"])
        .attr("stroke-width", attrDict["stroke-width"])
        .on("click", click)
        .on("mouseover", mouseover)
        .on("mouseout", mouseout);
    },
    drawText: (element, text, xOffset, yOffset, yOffsetIdx, textColor, textDecoration) => {
      return element
        .append('text')
        .attr("x", xOffset)
        .attr("y", yOffset * yOffsetIdx)
        .attr("fill", textColor)
        .attr("text-decoration", textDecoration)
        .text(text);
    },
    drawLine: (element, x1, y1, x2, y2, strokeColor, strokeWidth) => {
      return element
        .append("line")
        .attr("class", "line")
        .attr("x1", x1)
        .attr("y1", y1)
        .attr("x2", x2)
        .attr("y2", y2)
        .attr("stroke", strokeColor)
        .style("stroke-width", strokeWidth);
    },
    drawCircle: (element, data, radius, fillColor, click = () => { }, mouseover = () => { }, mouseout = () => { }) => {
      return element
        .selectAll(".circle")
        .data(data)
        .join("circle")
        .attr("r", radius)
        .attr("cx", (d) => d.x)
        .attr("cy", (d) => d.y)
        .attr("class", "circle")
        .style("fill", fillColor)
        .on("click", (d) => click(d))
        .on("mouseover", (d) => mouseover(d))
        .on("mouseout", (d) => mouseout(d));
    },
    drawXAxis: (element, xScale, numOfTicks, tickFormatFn, xOffset, yOffset, strokeColor) => {
      const axis = d3.axisBottom(xScale)
        .ticks(numOfTicks)
        .tickFormat(tickFormatFn);

      const line = element.append("g")
        .attr("class", "xAxis")
        .attr("transform", `translate(${xOffset}, ${yOffset})`)
        .call(axis);

      line.selectAll("path")
        .style("fill", "none")
        .style("stroke", strokeColor)
        .style("stroke-width", "1px");

      line.selectAll("line")
        .style("fill", "none")
        .style("stroke", strokeColor)
        .style("stroke-width", "1px");

      line.selectAll("text")
        .style("font-size", "12px")
        .style("font-family", "sans-serif")
        .style("font-weight", "lighter");

      return line;
    },
    drawToolTip: (element, event, text, width, height) => {
      const [mousePosX, mousePosY] = d3.pointer(event, element.node());
      const toolTipG = element
        .append("g")
        .attr("class", "tooltip")
        .attr("transform", `translate(${mousePosX}, ${mousePosY})`)

      toolTipG.append("rect")
        .attr("class", "tooltip-area")
        .attr("width", width)
        .attr("height", height)
        .attr("fill", "#fff")
        .attr("stroke", "#000");

      toolTipG.append("text")
        .attr("class", "tooltip-content")
        .style("font-family", "sans-serif")
        .style("font-size", "12px")
        .attr("fill", "#000")
        .text(text);
    },
    clearToolTip: (element) => {
      element.selectAll(".tooltip").remove();
    }
  }
});
