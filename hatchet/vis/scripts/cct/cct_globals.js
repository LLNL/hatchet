import * as d3 from 'd3v4';

const globals = Object.freeze({
    UNIFIED: 0,
    DEFAULT: 0,
    SUM: "sum",
    AVG: "avg",
    signals: {
        CLICK: "CLICK",
        COLLAPSESUBTREE: "COLLAPSESUBTREE",
        COMPOSEINTERNAL: "COMPOSEINTERNAL",
        BRUSH: "BRUSH",
        TOGGLEBRUSH: "TOGGLEBRUSH",
        COLLAPSE: "COLLAPSE",
        METRICCHANGE: "METRICCHANGE",
        TREECHANGE: "TREECHANGE",
        COLORCLICK: "COLORCLICK",
        LEGENDCLICK: "LEGENDCLICK",
        ENABLEMASSPRUNE: "ENABLEMASSPRUNE",
        REQUESTMASSPRUNE: "REQUESTMASSPRUNE",
        RESETVIEW: "RESET",
        PRUNERANGEUPDATE: "PRUNERANGEUPDATE",
        UPDATESELECTED: "UPDATESELECTED",
        SNAPSHOT: "SNAPSHOT",
        DECOMPOSENODE: "DECOMPOSENODE",
        TOGGLEMENU: "TOGGLEMENU"
    },
    layout: {
        margin: {top: 20, right: 20, bottom: 20, left: 20},
    },
    duration: 750
});

var makeSignaller = function() {
    let _subscribers = []; // Private member

    // Return the object that's created
    return {
        // Register a function with the notification system
        add: function(handlerFunction) {_subscribers.push(handlerFunction); },

        // Loop through all registered function and call them with passed
        // arguments
        notify: function(args) {
            for (var i = 0; i < _subscribers.length; i++) {
                try{
                    _subscribers[i](args);
                } catch(error){
                    console.error(error);
                }
            }
        }
    };
}


const digitAbbrevScale = d3.scaleOrdinal().range(["K", "K", "K", "M", "M", "M", "B", "B", "B", "T", "T", "T",]).domain(new Array(12).fill(0).map((_,i)=>i+4));

function getSigFigString(num){
    /**
     * Converts an integer or float to a string
     * with fixed number of figures before and after
     * the decimal point and an magnitude abbreviation.
     */
    if(num.toFixed(2).length <= 6){
        return num.toFixed(2);
    }
    else{
        let numdig = parseInt(num).toString().length;
        for(let i = 4; i <= numdig; i +=3){
            num = (parseInt(num)/1000);
        }
        let numstr = num.toFixed(2).toString();

        let abbrev = digitAbbrevScale(numdig);

        return numstr + abbrev;
    }
}

function areaToRad(area){
    /**
     * Converts area to radius. Used for accuracy in scaling
     * nodes.
     */
    return Math.sqrt(area/Math.PI);
}


var RT = window.Roundtrip;

export { makeSignaller, globals, RT, d3, getSigFigString, areaToRad};