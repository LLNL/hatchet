# Hatchet VIS Subdirectory

This folder contains all the code related to the interactive Jupyter visualizations deployed with the Hatchet Library.

## Development Requirements

The software in this subdirectory requires [Node.js and Node Package Manager](https://nodejs.org/en/download/) for the development and building of javascript code.

## Installing node packages

One you have Node and NPM installed on your system, you can install all necessary node packages by running the following line in your terminal from this directory:

```
npm install
```

## Building out javascript code with webpack

To build out javascript into the static bundles used by the Jupyter visualizations, run the following line from this directory in your terminal:

```
npm run build
```

Alterntinatively if you are developing a visualization, you can run the following line to force bundles to automatically update when you change the javascript source code:

```
npm run watch
```