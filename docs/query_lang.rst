.. Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
   Hatchet Project Developers. See the top-level LICENSE file for details.

   SPDX-License-Identifier: MIT

**************
Query Language
**************

.. versionadded:: 1.2.0

.. note::

   For more information about the query language, including some case studies leveraging it,
   check out `our paper <https://doi.org/10.1109/eScience55777.2022.00039>`_ from eScience 2022.

One of the most important steps in identifying performance phenomena (e.g., bottlenecks) is data subselection
and reduction. In previous versions of Hatchet, users could only reduce their data using filters on the
pandas :code:`DataFrame` component of the GraphFrame object. However, this type of data reduction
ignores the relational data encoded in the Graph component of the GraphFrame.

Hatchet's Call Path Query Language (*query language* for short) provides a new way of reducing profiling
data that leverages this relational data. In the query language, users provide a *query*, or a
description of the properties of one or more paths in the Graph. Hatchet then uses this query to
select all nodes in the Graph that satisfy the query. These nodes are returned to the user as a new
GraphFrame.

The following sections will describe the structure of a query, the syntaxes for constructing
queries, extra functionality to provided by basic queries, and the APIs for dealing with queries.

Query Structure
===============

The main input to the query language is a query. A *query* is defined as a sequence of *query nodes*.
A query node is a tuple of a *quantifier* and a *predicate*. A quantifier defines how many nodes in the
Graph should be matched to a single query node. A predicate defines what conditions must be satisfied
for a node in the Graph to match a query node.

.. _query_syntaxes:
Query Syntaxes and Dialects
===========================

Hatchet provides three ways of creating queries to simplify the use of the query language under
diverse circumstances (e.g., creating queries in JavaScript that will be moved into Python code).
The first way to create queries is the *base syntax*: a Python API for iteratively building a query
using method calls. Hatchet also provides two dialects for the query language:

- **Object-based Dialect**: uses Python built-in objects (i.e., :code:`list`, :code:`tuple`, :code:`dict`)
  to build queries
- **String-based Dialect**: uses strings to build queries. The syntax of this dialect is derived from
  the `Cypher <https://neo4j.com/product/cypher-graph-query-language/>`_ query language for graph databases.

Besides syntaxes, these three ways of creating queries differ in their capabilities. In general, the base syntax
is the most capable and most verbose. The object-based dialect is the least capable and least verbose, and the
string-based dialect is in-between. For a more complete breakdown of the capabilities, see the
:ref:`syntax_capabilities` section.

.. _base_syntax:
Base Syntax
-----------

.. note::
   In version 2023.1.0, the query language was refactored to work better with a new tool
   called `Thicket <https://thicket.readthedocs.io/en/latest/>`_. This refactor is explained in
   more detail in the :ref:`query_lang_apis` section.
   This section assumes the use of "new-style" query API. If you are using the "old-style" API, you
   can simply replace any use of :code:`Query` with :code:`QueryMatcher`.

Hatchet's :code:`Query` class defines how to construct a query using the base syntax. Using this class,
queries are built using the :code:`match` and :code:`rel` methods. The :code:`match` method sets the first
node of the query. The :code:`rel` method is called iteratively, each time adding a new node to the end
of the query. Both methods take a quantifier and a predicate as input.

A quantifier can have one of four possible values:

- :code:`"."`: match one node
- :code:`"*"`: match zero or more nodes
- :code:`"+"`: match one or more nodes
- An integer: match exactly that number of nodes

All queries can be constructed using just :code:`"."` and :code:`"*"`. The :code:`"+"` and integer quantifiers
are provided for convenience and are implemented as follows:

- :code:`"+"`: implemented as a node with a :code:`"."` quantifier followed by a node with a :code:`"*"` quantifier
- Integer: implemented as a sequence of nodes with :code:`"."` quantifiers

If no quantifier is provided to :code:`match` or :code:`rel`, the default :code:`"."` quantifier is used.

A predicate is represented as a Python :code:`Callable` that takes the data for a node in a GraphFrame
as input and returns a Boolean. The returned Boolean is used internally to determine whether a GraphFrame
node satisfies the predicate. If a predicate is not provided to :code:`match` or :code:`rel`, the default
predicate is a function that always returns :code:`True`.

The base syntax is illustrated by the query below. This query uses two query nodes to find all subgraphs in the
GraphFrame rooted at MPI (or PMPI) function calls that have more than 5 L2 cache misses (as measured by PAPI).

.. code-block:: python

   query = (
       Query()
       .match(
           ".",
           lambda row: re.match(
               "P?MPI_.*",
               row["name"]
           )
           is not None
           and row["PAPI_L2_TCM"] > 5
       )
       .rel("*")
   )

.. _obj_dialect:
Object-based Dialect
--------------------

The object-based dialect allows users to construct queries using built-in Python objects. In this dialect, a
query is represented by a Python :code:`list` of query nodes. Each query node is represented by a Python
:code:`tuple` of a quantifier and a predicate. Quantifiers are represented the same way as in the base syntax
(see the :ref:`base_syntax` section for more information). Predicates are represented as key-value pairs where keys
are metric names and values are Boolean expressions generated using the following rules:

- If the metric is numeric, the value can be a be a number (checks for equality) or a string consisting of a
  comparison operator (one of :code:`<`, :code:`<=`, :code:`==`, :code:`>`, or :code:`>=`) followed by a number
- If the metric is a string, the value can be any regex string that is a valid input to `Python's re.match
  function <https://docs.python.org/3/library/re.html#re.match>`_.

Multiple predicates can be combined into a larger predicate by simply putting multiple key-value pairs into
the same Python :code:`dict`. When multiple predicates are in the same :code:`dict` in the object-based dialect,
they are all combined by conjunction (i.e., logical AND).

When using a default quantifier (i.e., :code:`"."`) or predicate (i.e., a function that always returns :code:`True`),
query nodes do not have to be represented as a Python :code:`tuple`. In these situations, a query node is represented
by simply adding the non-default component to the Python :code:`list` representing the query.

The object-based dialect is illustrated by the query below. This query is the same as the one introduced in the
:ref:`base_syntax` section. It uses two query nodes to find all subgraphs in the GraphFrame rooted at MPI (or PMPI)
function calls that have more than 5 L2 cache misses (as measured by PAPI).

.. code-block:: python

   query = [
       (
           ".",
           {
               "name": "P?MPI_.*",
               "PAPI_L2_TCM": "> 5"
           }
       ),
       "*"
   ]

.. _str_dialect:
String-based Dialect
--------------------

.. versionadded:: 2022.1.0

The string-based dialect allows users to construct queries using strings. This allows the string-based dialect
to be the only way of creating queries that is not tied to Python. The syntax of the query strings in the
string-based dialect is derived from `Cypher <https://neo4j.com/product/cypher-graph-query-language/>`_.
A query in this dialect contains two main syntactic pieces: a :code:`MATCH` statement and a :code:`WHERE`
statement.

The :code:`MATCH` statement starts with the :code:`MATCH` keyword and defines the quantifiers and variable
names used to refer to query nodes in the predicates. Each node in the :code:`MATCH` statement takes the form
of :code:`(<quantifier>, <variable>)`. Quantifiers in the string-based dialect have the same representation
as the base syntax and object-based dialect. Variables can be any valid combination of letters, numbers, and underscores
that does not start with a number (i.e., normal variable name rules). Multiple query nodes can be added to the
:code:`MATCH` statement by chaining the nodes with :code:`->`.

The :code:`WHERE` statement starts with the :code:`WHERE` keyword and defines one or more predicates.
Predicates in the string-based dialect are represented by expressions of the form :code:`<variable>."<metric>" <comparison operation>`.
In these expressions, :code:`<variable>` should be replaced by the variable associated with the desired query node
from the :code:`MATCH` statement, and :code:`<metric>` should be replaced by the name of the metric being considered.
:code:`<comparison operation>` should be replaced by one of the following:

- :code:`= <value>`: checks if the metric equals a value
- :code:`STARTS WITH <substring>`: checks if a string metric starts with a substring
- :code:`ENDS WITH <substring>`: checks if a string metric ends with a substring
- :code:`CONTAINS <substring>`: checks if a string metric contains a substring
- :code:`=~ <regex>`: checks if a string metric matches a regex
- :code:`< <value>`: checks if a numeric metric is less than a value
- :code:`<= <value>`: checks if a numeric metric is less than or equal to a value
- :code:`> <value>`: checks if a numeric metric is greater than a value
- :code:`>= <value>`: checks if a numeric metric is greater than or equal to a value
- :code:`IS NAN`: checks if a numeric metric is NaN
- :code:`IS NOT NAN`: checks if a numeric metric is not NaN
- :code:`IS INF`: checks if a numeric metric is infinity
- :code:`IS NOT INF`: checks if a numeric metric is not infinity
- :code:`IS NONE`: checks if a metric is Python's None value
- :code:`IS NOT NONE`: checks if a metric is not Python's None value

.. note::
   .. versionadded:: 2022.2.1
      Added the comparison operations :code:`IS LEAF` and :code:`IS NOT LEAF`, which check
      whether a node is a leaf node of the GraphFrame.

Multiple predicates can be combined using three Boolean operators: conjunction (i.e., :code:`AND` keyword),
disjunction (i.e., :code:`OR` keyword), and complement (i.e., :code:`NOT` keyword).

The string-based dialect is illustrated by the query below. This query is the same as the one introduced in the
:ref:`base_syntax` section. It uses two query nodes to find all subgraphs in the GraphFrame rooted at MPI (or PMPI)
function calls that have more than 5 L2 cache misses (as measured by PAPI).

.. code-block:: python

   query = """
   MATCH (".", p)->("*")
   WHERE p."name" STARTS WITH "MPI_" OR p."name" STARTS WITH "PMPI_" AND
       p."PAPI_L2_TCM" > 5
   """

.. note::

   The string-based dialect is **case-sensitive**.

.. _applying_queries:
Applying Queries to GraphFrames
===============================

Queries are applied to the data in a GraphFrame using the :code:`GraphFrame.filter()` method.
This method takes a "filter object" as its first argument. A filter object can be one of the following:

- A Python :code:`Callable`: filters the data in the GraphFrame using a filter on the DataFrame
  (*does not use the query language*)
- A string: assumes the argument is a string-dialect query, builds a new-style query object from the argument,
  and applies that query to the GraphFrame
- A Python :code:`list`: assumes the argument is an object-dialect query, builds a new-style query object from the argument,
  and applies that query to the GraphFrame
- A new-sytle or old-style query object: applies the query to the GraphFrame

When providing a query, the call to :code:`GraphFrame.filter()` will return a new GraphFrame
containing the nodes from *all* paths in the original GraphFrame that match the properties
described by the query.

Additional Query Language Functionality
=======================================

This section covers several types of functionality that the query language provides beyond the core querying
covered by the :ref:`query_syntaxes` and :ref:`applying_queries` sections.

.. _compound_queries:
Combining Query Results with Compound Queries
---------------------------------------------

.. versionadded:: 2022.1.0

.. note::

   This section assumes the use of the "new-style" query APIs. If using the "old-style" API, simply replace
   the query classes detailed in this section with their equivalents from the old-style API.
   For more information about the new-style and old-style APIs, see the :ref:`query_lang_apis` section.

Sometimes, a user might want to combine the results of multiple queries together to get a more detailed
picture of their performance data. To enable this, the query language provides "compound queries". A compound
query is a type of query that modifies the results of one or more other queries using a set operation. Currently,
the query language provides the following Python classes for creating compound queries:

- :code:`ConjunctionQuery`: combines the results of two or more sub-queries using
  set conjunction (i.e., logical AND)
- :code:`DisjunctionQuery`: combines the results of two or more sub-queries using
  set disjunction (i.e., logical OR)
- :code:`ExclusiveDisjunctionQuery`: combines the results of two or more sub-queries using
  exclusive set disjunction (i.e., logical XOR)
- :code:`NegationQuery`: modifies the results of a single sub-query using set negation (i.e., logical NOT)

A compound query can be created in one of two ways. First, all the sub-queries can be passed into
the constructor of a compound query class. An example of this is shown below. This example creates
a :code:`DisjunctionQuery` object from two string-based dialect queries. The first query looks for
all subgraphs rooted at MPI nodes, and the second query looks for all subgraphs rooted at CUDA host
functions (i.e., functions starting with the :code:`cuda` or :code:`cu` prefixes). So, the
:code:`DisjunctionQuery` can be used to look at the host-side internals of a MPI+CUDA program.

.. code-block:: python

   query_mpi = """
   MATCH (".", p)->("*")
   WHERE p."name" STARTS WITH "MPI_"
   """
   query_cuda_host = """
   MATCH (".", p)->("*")
   WHERE p."name" STARTS WITH "cuda" or p."name" STARTS WITH "cu"
   """
   disjunction_query = hatchet.query.DisjunctionQuery(query_mpi, query_cuda_host)

The other way to create a compound query is to use Python's built-in binary operators. The following list
shows the operators supported for compound queries and how they map to compound query classes:

- :code:`&` = :code:`ConjunctionQuery`
- :code:`|` = :code:`DisjunctionQuery`
- :code:`^` = :code:`ExclusiveDisjunctionQuery`
- :code:`~` = :code:`NegationQuery`

The code block below shows the same :code:`DisjunctionQuery` query example as above using binary operators.

.. code-block:: python

   query_mpi = """
   MATCH (".", p)->("*")
   WHERE p."name" STARTS WITH "MPI_"
   """
   query_cuda_host = """
   MATCH (".", p)->("*")
   WHERE p."name" STARTS WITH "cuda" or p."name" STARTS WITH "cu"
   """
   disjunction_query = query_mpi | query_cuda_host

Supporting Compound Queries through the String-based Dialect
------------------------------------------------------------

.. versionadded:: 2022.1.0

When using the string-based dialect, compound queries do not need to be created using the compound query
classes described in the :ref:`compound_queries` section. Instead, compound queries can be created
directly within the string-based dialect using curly braces and the :code:`AND`, :code:`OR`, and :code:`XOR`
keywords.

When creating compound queries from the string-dialect, curly braces should be placed around either
entire string-based dialect queries (i.e., both the :code:`MATCH` and :code:`WHERE` statements) or
around subsets of the predicate in the :code:`WHERE` statement. When wrapping entire string-based
dialect queries, each wrapped region is treated as a sub-query. When wrapping subsets of the predicate
in the :code:`WHERE` statement, sub-queries are created by combining the unwrapped :code:`MATCH` statement
with each wrapped subset in the :code:`WHERE` statement. This can be thought of as the :code:`MATCH`
statement being shared between the wrapped subsets in the :code:`WHERE` statement.

Curly brace-delimited regions of a string-based query should then be separated using the :code:`AND`,
:code:`OR`, and :code:`XOR` keywords. When used to separate curly brace-delimited regions, these keywords
map to compound query classes as follows:

- :code:`AND` = :code:`ConjunctionQuery`
- :code:`OR` = :code:`DisjunctionQuery`
- :code:`XOR` = :code:`ExclusiveDisjunctionQuery`

To illustrate this functionality, consider the MPI+CUDA example from the :ref:`compound_queries` section.
When placing curly braces around entire string-based dialect subqueries, this example can be rewritten
as follows:

.. code-block:: python

   query_mpi_and_cuda = """
   {MATCH (".", p)->("*") WHERE p."name" STARTS WITH "MPI_"} OR
   {MATCH (".", p)->("*") WHERE p."name" STARTS WITH "cuda" or p."name" STARTS WITH "cu"}
   """

Similarly, when placing curly braces around subsets of the predicate in the :code:`WHERE` statement,
this example can be rewritten as follows:

.. code-block:: python

   query_mpi_and_cuda = """
   MATCH (".", p)->("*")
   WHERE {p."name" STARTS WITH "MPI_"} OR {p."name" STARTS WITH "cuda" or p."name" STARTS WITH "cu"}
   """

Compound queries in the string-based dialect cannot be wrapped in query language classes by simply
passing them to constructors. Instead, these types of compound queries can be wrapped in classes
using the :code:`parse_string_dialect` function. This function accepts a string-based dialect
query as its only required argument and returns either a :code:`StringQuery` object (when there are no curly
brace-delimited regions in the input query) or a compound query object (when there are curly
brace-delimited regions in the input query). If a query language class is not needed, compound
queries in the string-based dialect can simply be applied to a GraphFrame as usual with
:code:`GraphFrame.filter()`.

.. _multi_index_gf:
Supporting Multi-Indexed GraphFrames in the Object- and String-based Dialects
-----------------------------------------------------------------------------

.. versionadded:: 2023.1.0

As explained in the :ref:`user_guide`, the DataFrame component of the GraphFrame often uses a multiindex
to represent data for multiprocessed and/or multithreaded applications. However, this multiindexed data
is difficult to work with in query language predicates. For example, consider the following base syntax
predicate:

.. code-block:: python

   predicate1 = lambda row: row["time"] > 5

This predicate simply checks if a node's "time" metric is greater than 5.
This predicate makes sense for non-multiindexed data because there is only one row of data in the
DataFrame for a given node and, thus, only one value for each metric for that node. In other words,
metrics are scalar for a given node when dealing with non-multiindexed data. However, when dealing
with multiindexed data, there are multiple rows for a given node, and, as a result, each metric is
effectively a vector.

Since version 1.2.0, handling this type of multiindexed data has only been supported in the base syntax
because of the flexibility it provides by being a programmatic interface. For example, the predicate
above can be rewritten for multiindexed data as follows:

.. code-block:: python

   predicate1 = lambda node_data: node_data["time"].apply(lambda x: x > 5).all()

This predicate checks that *all* values for a node's "time" metric are greater than 5.
As the example above illustrates, one important consideration when dealing with multiindexed data
is how to reduce a vector of metric data into the scalar Boolean value required by the query language.
Because the base syntax requires users to write the Python code for their predicates, it allows users
to make that decision easily. Unfortunately, the object- and string-based dialects do not provide the
same flexibility because they intentionally require the user to not write Python code. For this reason,
the dialects previously have not supported multiindexed GraphFrames, and users were required to reduce
their data to a non-multiindexed GraphFrame (e.g., through :code:`GraphFrame.drop_index_levels`) before
applying a query in either dialect.

However, with the introduction of the new-style query API in version 2023.1.0 (see the :ref:`query_lang_apis`
section for more information), it is now possible to use multiindexed GraphFrames with the object- and
string-based dialects. To do so, users must provide the new :code:`multi_index_mode` parameter
to the :code:`GraphFrame.filter()` method, the :code:`ObjectQuery` class, or the :code:`StringQuery` class.
This parameter controls how predicates generated from the dialects will treat multiindexed data.
It can be set to one of three values:

- :code:`"off"`
- :code:`"all"`
- :code:`"any"`

When set to :code:`"off"` (which is the default), the generated predicates will assume
that the data for each node is **not** multiindexed. This behavior is the same as eariler versions of Hatchet.
When set to :code:`all`, the generated predicates will require that all rows of data for a given node
satisfy the predicate. This usually amounts to applying the predicate to a node's data
with pandas' :code:`Series.apply()` and reducing the resulting :code:`Series` with :code:`Series.all()`.
Finally, when :code:`multi_index_mode` is set to :code:`"any"`, the generated predicates will require
that one or more rows of data for a given node satisfy the predicate. This usually amounts to applying
the predicate to a node's data with pandas' :code:`Series.apply()` and reducing the resulting :code:`Series`
with :code:`Series.any()`.

.. warning::

   The old-style query API still does **not** support multiindexed GraphFrames for the object-
   and string-based dialects. When using multiindexed GraphFrames, users must either use the new-style
   query API or the base syntax support in the old-style query API's :code:`QueryMatcher` class.

.. _query_lang_apis:
Query Language APIs
===================

.. versionchanged:: 2023.1.0

In version 2023.1.0, the query language underwent a large refactor to enable support for GraphFrame objects
containing a multi-indexed DataFrame (see the :ref:`multi_index_gf` section for more information).
As a result, the query language now has two APIs:

- New-Style Query API: for the query language starting with version 2023.1.0
- Old-Style Query API: for the query language prior to version 2023.1.0

The old-style API is discouraged for new users. However, these APIs are not deprecated at this time. For the time
being, the old-style API will be maintained as a thin wrapper around the new-style API.

The key changes in the new-style API that are exposed to users are:

- The creation of a new dedicated :code:`ObjectQuery` class to represent object-based dialect queries
- The renaming of compound query classes and the elimination of confusing alias classes

All other changes in the new-style API are either minor changes (e.g., renaming) or internal changes that
are not visible to end users.

The table below shows the classes and functions of the new- and old-style APIs and how they map to one another.

+-----------------------------------+----------------------------+------------------------------------------------------------------------+
| New-Style API                     | Old-Style API              | Description                                                            |
+===================================+============================+========================================================================+
| :code:`Query`                     | :code:`QueryMatcher`       | Implements the base syntax                                             |
+-----------------------------------+                            +------------------------------------------------------------------------+
| :code:`ObjectQuery`               |                            | Parses the object-based dialect and converts it into the base syntax   |
+-----------------------------------+----------------------------+------------------------------------------------------------------------+
| :code:`StringQuery`               | :code:`CypherQuery`        | Parses the string-based dialect and converts it into the base syntax   |
+-----------------------------------+----------------------------+------------------------------------------------------------------------+
| :code:`parse_string_dialect`      | :code:`parse_cypher_query` | Parses either normal string-based dialect queries or compound          |
|                                   |                            | queries in the string-based dialect into classes                       |
+-----------------------------------+----------------------------+------------------------------------------------------------------------+
| :code:`ConjunctionQuery`          | :code:`AndQuery`           | Combines sub-queries with set conjunction (i.e., logical AND)          |
|                                   | :code:`IntersectionQuery`  |                                                                        |
+-----------------------------------+----------------------------+------------------------------------------------------------------------+
| :code:`DisjunctionQuery`          | :code:`OrQuery`            | Combines sub-queries with set disjunction (i.e., logical OR)           |
|                                   | :code:`UnionQuery`         |                                                                        |
+-----------------------------------+----------------------------+------------------------------------------------------------------------+
| :code:`ExclusiveDisjunctionQuery` | :code:`XorQuery`           | Combines sub-queries with exclusive set disjunction (i.e., logical XOR |
|                                   | :code:`SymDifferenceQuery` |                                                                        |
+-----------------------------------+----------------------------+------------------------------------------------------------------------+
| :code:`NegationQuery`             | :code:`NotQuery`           | Modifies a single sub-query with set negation (i.e., logical NOT)      |
+-----------------------------------+----------------------------+------------------------------------------------------------------------+

The only other changes that may impact users are changes to the base classes of the classes in the table above.
In the old-style API, all classes in the query language inherit from :code:`AbstractQuery`. As a result,
:code:`isinstance(obj, hatchet.query.AbstractQuery)` or :code:`issubclass(type(obj), hatchet.query.AbstractQuery)`
can be used to check if a Python object is an old-sytle API query object. In the new-style API, "normal" queries
(i.e., :code:`Query`, :code:`ObjectQuery`, and :code:`StringQuery`) and compound queries
(i.e., :code:`ConjunctionQuery`, :code:`DisjunctionQuery`, :code:`ExclusiveDisjunctionQuery`, and
:code:`NegationQuery`) inherit from the :code:`Query` and :code:`CompoundQuery` classes respectively.
As a result, to check if a Python object is a new-sytle API query object (either normal or compound),
the following piece of code can be used:

.. code-block:: python

   issubclass(type(obj), hatchet.query.Query) or issubclass(type(obj), hatchet.query.CompoundQuery)

Since the :code:`GraphFrame.filter()` method works with either API, the :code:`is_hatchet_query` function
is provided to conveniently check if a Python object is any type of query language object, regardless
of API.

.. _syntax_capabilities:
Syntax and Dialect Capabilities
===============================

.. warning::

   Section in-progress

Along with different syntaxes, the base syntax, object-based dialect, and string-based dialect also
have different capabilities. In other words, there are things that each way of writing queries can and
cannot do. To help users understand these capabilities, the ways of writing queries
have been classified in terms of their properties and logical operators.

Properties are classified into five categories, one for quantifiers and four for predicates. These
categories are:

- *Quantifier Capabilities*: ability to match different numbers of nodes (i.e., match one, zero or more
  one or more, or an exact number of nodes)
- *String Equivalence and Regex Matching Predicates*: ability to check if the value of a specified string
  metric is equal to a provided string or matches a provided regular expression
- *String Containment Predicates*: ability to check if the value of a specified string metric starts
  with, ends with, or contains a provided string
- *Basic Numeric Comparison Predicates*: ability to check if the value of the specified numeric metric
  satisfies the numeric comparison (e.g., equal to, greater than, greater than or equal to)
- *Special Value Identification Predicates*: ability to check if the value of the specified metric
  is equivalent to the provided "special value" (i.e., NaN, infinity, None, or "leaf")

The table below shows whether each way of creating queries supports each property category.

+----------------------------------------+-------------+-----------------------+----------------------+
| Property Category                      | Base Syntax | Object-based Dialect  | String-based Dialect |
+========================================+=============+=======================+======================+
| Quantifier Capabilities                | ✅          | ✅                    | ✅                   |
+----------------------------------------+-------------+-----------------------+----------------------+
| String Equivalence and Regex           | ✅          | ✅                    | ✅                   |
| Matching Predicates                    |             |                       |                      |
+----------------------------------------+-------------+-----------------------+----------------------+
| String Containment Predicates          | ✅          |                       | ✅                   |
+----------------------------------------+-------------+-----------------------+----------------------+
| Basic Numeric Comparison Predicates    | ✅          | ✅                    | ✅                   |
+----------------------------------------+-------------+-----------------------+----------------------+
| Special Value Identification           | ✅          |                       | ✅                   |
| Predicates                             |             |                       |                      |
+----------------------------------------+-------------+-----------------------+----------------------+

Logical operators are classified into three categories. These categories are:

- *Predicate Combination through Conjunction*: ability to combine predicates using conjuntion (i.e., logical AND)
- *Predicate Combination through Disjunction and Complement*: ability to combine predicates using
  disjunction (i.e., logical OR) or find the complement (i.e., logical NOT) to a single predicate
- *Predicate Combination through Other Operations*: ability to combine predicates through other
  means, such as exclusive disjunction (i.e., logical XOR)

+----------------------------------------+-------------+-----------------------+----------------------+
| Logical Operator Category              | Base Syntax | Object-based Dialect  | String-based Dialect |
+========================================+=============+=======================+======================+
| Predicate Combination through          | ✅          | ✅                    | ✅                   |
| Conjunction                            |             |                       |                      |
+----------------------------------------+-------------+-----------------------+----------------------+
| Predicate Combination through          | ✅          |                       | ✅                   |
| Disjunction and Complement             |             |                       |                      |
+----------------------------------------+-------------+-----------------------+----------------------+
| Predicate Combination through          | ✅          |                       |                      |
| Other Operations                       |             |                       |                      |
+----------------------------------------+-------------+-----------------------+----------------------+

Query Language Examples
=======================

This section shows some examples of common queries that users may want to perform.
They can be used as a starting point for creating more complex queries. All of these
examples are designed to be applied to the following data presented in the :ref:`user_guide` page.

.. table::
   :align: center
   :widths: auto

   +-------------------------------------+-------------------------------+
   | .. image:: images/vis-terminal.png  | .. image:: images/vis-dot.png |
   |    :scale: 50%                      |    :scale: 35%                |
   |    :align: left                     |    :align: right              |
   +-------------------------------------+-------------------------------+

Find a Subgraph with a Specific Root
------------------------------------

This example shows how to find a subgraph of a GraphFrame starting with a specific root.
More specifically, the queries in this example can be used to find the subgraph rooted at
nodes representing MPI or PMPI function calls.

.. tabs::

   .. tab:: Base Syntax

      .. code-block:: Python

         query = (
             Query()
             .match(
                 ".",
                 lambda row: re.match(
                     "P?MPI_.*",
                     row["name"]
                 )
                 is not None
                 and row["PAPI_L2_TCM"] > 5
             )
             .rel("*")
         )

   .. tab:: Object-based Dialect

      .. code-block:: python

         query = [
             (
                 ".",
                 {
                     "name": "P?MPI_.*",
                     "PAPI_L2_TCM": "> 5"
                 }
             ),
             "*"
         ]

   .. tab:: String-based Dialect

      .. code-block:: python

         query = """
         MATCH (".", p)->("*")
         WHERE p."name" STARTS WITH "MPI_" OR p."name" STARTS WITH "PMPI_" AND
             p."PAPI_L2_TCM" > 5
         """

When applying one of these queries to the example data, the resulting GraphFrame looks like this:

TBA

Find All Paths Ending with a Specific Node
-------------------------------------------

TBA

Find All Nodes for a Particular Software Library
-----------------------------------------------

TBA

Find All Paths through a Specific Node
---------------------------------------

TBA
