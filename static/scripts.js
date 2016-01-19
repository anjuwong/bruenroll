function populateDepts() {
    var depts = [];
    $.getJSON('/_get_departments',function(data) {
        $.each(data, function(index, obj) {
            var dept = document.createElement('a');
            dept.setAttribute('href', '#');
            dept.setAttribute('class', 'list-group-item');


            dept.innerHTML = "<dept class='list-group-item-heading'>" + obj + "</dept>";
            depts.push(dept);
        });
        $('#dept-list').append(depts);
    });
    return false;
}

function populateCourses(trm, yr, dpt) {
    var courses = [];
    $('#course-list').fadeOut();
    $.getJSON('/_get_courses', {term: trm, year: yr, dept: dpt},function(data) {
            $.each(data, function(index, obj) {
            var crs = document.createElement('a');
            crs.setAttribute('href', '#');
            crs.setAttribute('class', 'list-group-item');

            // Create a closure with the JSON db entry so they can be displayed dynamically
            crs.onclick = (function() {
                var crsObj = obj;
                return function() {
                    showStats(crsObj);
                }
            })();
            crs.innerHTML = "<crs class='list-group-item-heading'>" + obj.title + "</crs>" + "<p class='list-group-item-text'>" + obj.prof + "<br>" + obj.timestart + " - " + obj.timeend + "</p>";
            courses.push(crs);
        });
        $('#course-list').empty();
        $('#course-list').append(courses);
        $('#course-list').fadeIn();
    });
    return false;
}

function showStats(obj) {
    var margin = {top:50, right: 50, bottom:50, left:50};
    var width=500;
    var height=500;
    var data = counts2Array(obj.enrollsdaycount, obj.enrolls);
    var x = d3.scale.linear().range([0, width]);
    var y = d3.scale.linear().range([height, 0]);
    var xAxis = d3.svg.axis()
                  .scale(x)
                  .ticks(data.length)
                  .orient("bottom");
    var yAxis = d3.svg.axis()
                  .scale(y)
                  .orient("left");

    var line = d3.svg.line()
        .x(function(d) {return x(d.count);})
        .y(function(d) {return y(d.enroll);});

    d3.select("#svg-container").select("svg").remove();
    var svg = d3.select('#svg-container')
                .append("svg")
                .attr('width', width+margin.left+margin.right)
                .attr('height',height+margin.top+margin.bottom)
                .append("g")
                .attr("transform","translate(" + margin.left+ "," + margin.top + ")");

    var div = d3.select('#svg-container')
                .append('div')
                .attr('class', 'tooltip')
                .style('opacity', 0);

    y.domain([0,d3.max(data, function(d) {return d.enroll;})]);
    x.domain([0,d3.max(data,function(d) {return d.count;})]);


    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis)
        .append("text")
        .attr("x", 6)
        .attr("dx", ".71em");

    svg.append("g")
        .attr("class", "y axis")
        .call(yAxis)
        .append("text")
        .attr("transform", "rotate(-90)")
        .attr("y", 6)
        .attr("dy", ".71em")
        .style("text-anchor", "end")
        .text("Enrollment");

    svg.append("path")
        .datum(data)
        .attr("class", "line")
        .attr("d", line);

    svg.selectAll("dot")
        .data(data).enter().append("circle")
        .attr("r", 5)
        .attr("cx", function(d) { return x(d.count);})
        .attr("cy", function(d) {return y(d.enroll);})
        .on("mouseover", function(d) {
            div.transition()
                .duration(200)
                .style("opacity", .9);
            div.html("Enrollment:<br>" +  d.enroll)
                .style("left", (d3.event.pageX) + "px")
                .style("top", (d3.event.pageY) + "px");
        })
        .on("mouseout", function(d) {
            div.transition()
                .duration(500)
                .style("opacity", 0);
         });

    console.log(obj);
}

function counts2Array(counts, enrolls) {
    var arr = [];
    var counter = 1;
    for (i = 0; i < counts.length; i++) {
        for (c = 0; c < counts[i]; c++) {
            arr.push({enroll: enrolls[i], count:counter});
            counter += 1;
        }
    }
    return arr;
}