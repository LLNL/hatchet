//d3.v4
import { RT, d3 } from './cct/cct_globals';
import Controller from './cct/cct_controller';
import Model from './cct/cct_model';
import MenuView from './cct/cct_menu_view';
import ChartView from './cct/cct_chart_view';
import TooltipView from './cct/cct_tooltip_view';

d3.select(element).attr('width', '100%');

RT['jsNodeSelected'] = JSON.stringify(["*"]);

// ---------------------------------------------
// Main driver area 
// ---------------------------------------------

//model
var model = new Model();
//controller
var cont = new Controller(model);
//views
var menu = new MenuView(element, model);
var tooltip = new TooltipView(element, model);
var chart = new ChartView(element, model);

//register signallers 
menu.register(cont.dispatcher());
chart.register(cont.dispatcher());

model.register(menu.renderer());
model.register(chart.renderer());
model.register(tooltip.renderer());

//render all views one time
menu.render();
tooltip.render();
chart.render();