import * as d3 from 'd3v4';


const globals = Object.freeze({
    UNIFIED: 0,
    DEFAULT: 0,
    SUM: "sum",
    AVG: "avg",
    signals: {
        CLICK: "CLICK",
        DBLCLICK: "DBLCLICK",
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
        PRUNERANGEUPDATE: "PRUNERANGEUPDATE"
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
                _subscribers[i](args);
            }
        }
    };
}


var RT = window.Roundtrip;

export { makeSignaller, globals, RT, d3 };