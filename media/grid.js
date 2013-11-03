/**
 * Initializes web page; binds functions to links.
 */

$(document).ready(function() {

	window.TAG_NORMAL = $("#alltags").width();
	window.TAG_EXPANDED = window.TAG_NORMAL + 13;

	$.ajax({
		type: "GET",
		dataType: "html",
		url: "/ajax/poll/current",
		success: function(r) {
			$("div #poll").html(r);
		}
	});

	function hash_of(url) { // IE6 YET AGAIN
		return url.substring(url.indexOf("#"));
	}

	function syncForLink(link) {
		function make_relative(url) {
			if (url.match("http://")) {
				url = url.substring(7);
				url = url.substring(url.indexOf("/"));
			}
			return url.length < 2 ? '' : url;
		}
		var url = make_relative(link.attr("href"));
		var page_match = url.match(/^\/[0-9]+$/);
		if (page_match) { // paginated root
			var page = page_match.toString().substring(1);
			State.sync({'page': page}, {'link': link});
		} else if (url) {
			State.sync({'url': url}, {'link': link});
		} else { // front page
			new State(null, {'link': link});
		}
	}

	$(document).on("click", 'a.list-hider', function(event) {
		event.preventDefault();
		$(".alist").show("slow");
		$(".list-hider").hide();
	});

	$(document).on("click", 'a.list-hider', function(event) {
		if (is_nonlocal(event))
			return;
		event.preventDefault();
		var choice_id = hash_of($(this).attr("href")).substring(8); // #choice_
		$(this).addClass("active");
		$.ajax({
			type: "GET",
			dataType: "html",
			url: "/ajax/poll",
			data: {"choice": choice_id},
			success: function(r) {
				$("div #poll").html(r);
			},
			error: function(xhr) {
				$("div #poll").html(xhr.responseText);
			}
		});
	});

	$(document).on("click", 'a.poll_results_only', function(event) {
		if (is_nonlocal(event))
			return;
		event.preventDefault();
		var poll_id = hash_of($(this).attr("href")).substring(6); // #poll_
		$(this).addClass("active");
		$.ajax({
			type: "GET",
			dataType: "html",
			url: "/ajax/poll",
			data: {"poll": poll_id},
			success: function(r) {
				$("div #poll").html(r);
			},
			error: function(xhr) {
				$("div #poll").html(xhr.responseText);
			}
		});
	});

	$(document).on("click",'a.authorlink', function(event) {
		if (is_nonlocal(event))
			return;
		var page_author = $("#authorslug").html();
		var author = $(this).attr("data-slug");
		event.preventDefault();
		if ($(this).hasClass("showall")) {
			State.sync({'tags': [], 'date_min': DATE_MIN, 'date_max': DATE_MAX, 'author': $(this).attr('data-slug')}, {'link': $(this)});
			State.scrollup();
			return;
		} else if (page_author == author && $(".results").is(":visible")) {
			window.scroll(0,0);
			var old = $("#infobox").css('background-color');
			function a() { $("#infobox").css('background-color', 'white'); }
			function b() { $("#infobox").css('background-color', old); }
			var i = 50;
			setTimeout(a, 1*i);
			setTimeout(b, 2*i);
			setTimeout(a, 3*i);
			setTimeout(b, 4*i);
			setTimeout(a, 5*i);
			setTimeout(b, 6*i);
			setTimeout(a, 7*i);
			setTimeout(b, 8*i);
			return;
		} else {
			State.sync({'author': $(this).attr('data-slug')}, {'link': $(this)});
			State.scrollup();
		}
	});

	$(document).on("click",'a.embeddable', function(event) {
		if (is_nonlocal(event))
			return;
		event.preventDefault();
		syncForLink($(this));
		State.scrollup();
	});

	$(document).on("click",'.backinfobox', function(event) {
		State.sync({'author': $(this).attr('data-slug')}, {'link': $(this)});
		State.scrollup();
	});

	$(document).on("click",'.clearinfobox', function(event) {
		State.sync({'author': '', 'page': 1}, {'link': $(this)});
	});

	$(document).on("click",'a.pagelink', function(event) {
		if (is_nonlocal(event))
			return;
		event.preventDefault();
		State.sync({'page': $(this).attr("id").substring(2)}, {'link': $(this)});
		State.scrollup();
	});

	$(document).on("click",'a.gs-title', function(event) {
		if (is_nonlocal(event))
			return;
		var href = $(this).attr("href");
		var stripped = href.match("q=([^&]*)");
		if (stripped) {
			href = stripped[1];
		}
		if (href.match(/\.[a-z]+$/)) {
			$(this).attr("target", null);
			return; // it's probably non-html
		}
		event.preventDefault();
		$(this).attr("href", href);
		syncForLink($(this));
		State.scrollup();
	});

	// delete noscript compatibility links
	$("a.pagelink").map(function() {
		var stripped = $(this).attr("href").substring($(this).attr("href").search("#"));
		$(this).attr("href", stripped);
	});

	var selecting_dates = false;
	var down = false;
	$("#tags #alltags").width(window.TAG_EXPANDED);
	//$("#tags").disableTextSelect();
	//$("#dates").disableTextSelect();

	if (window.location.hash.length > 1) { // permalink and not lone '#'
		setVisible("none");
		new State(Repr.deserialize(window.location.hash), {'keep_hash': true});
	}

	/* HISTORY BEGINS - all State changes must be done */
	State.init_history_monitor();

	$("#tags li").not("#alltags").click(function(event) {
		if (is_nonlocal(event))
			return;
		event.preventDefault();
		if ($(this).hasClass("useless") && !$(this).hasClass("activetag"))
			$("#tags .activetag").not("#alltags").removeClass("activetag");
		tagslug = $(this).attr("id");
		if (!$(".results").is(":visible"))
			$(this).removeClass("activetag");
		$(this).removeClass("useless").toggleClass("activetag");
		State.sync(null, {'link': $(this)});
		State.scrollup();
	});

	$("#tags #alltags").click(function(event) {
		event.preventDefault();
		$("#dates li").removeClass("activedate");
		selecting_dates = false;
		$("#tags li").removeClass("useless");
		$("#tags .activetag").removeClass("activetag");
		new State(new Repr({'page': 1}), {'link': $(this)});
		State.scrollup();
	});

	$("#tags li a").click(function(event) {
		if (is_nonlocal(event))
			return;
		event.preventDefault();
	});

	$("#dates h3").click(function(event) {
		event.preventDefault();
		var min = ($(this).text().substring(5) - 1) + "08";
		var max = $(this).text().substring(5) + "07"; // year_
		var some_newly_selected = false;
		if (!State.select_dates(min, max)[0])
			$("#dates li").removeClass("activedate");
		State.sync(null, {'link': $("#dates li").filter(".activedate")});
	});

	$("#dates li li").mousedown(function() {
		if (!selecting_dates) {
			if ($(this).hasClass("activedate"))
				down = $(this).attr("id");
			else
				down = false;
			$("#dates li").removeClass("activedate");
			$(this).addClass("activedate");
			selecting_dates = true;
		}
	});

	$("#dates li li").mousemove(function() {
		if (selecting_dates)
			$(this).addClass("activedate");
	});

	$("#dates li").mouseup(function() {
		if (down == $(this).attr("id")) {
			$(this).removeClass("activedate");
		} else if (selecting_dates) {
			$(this).addClass("activedate");
		}
		if (selecting_dates) {
			selecting_dates = false;
			State.sync(null, {'link': $("#dates li").filter(".activedate")});
		}
	});

	$("#issue_thumbs").hover(function(event) {
		$("#issue_thumbs").css('opacity', 0.9);
	}, function(event) {
		$("#issue_thumbs").css('opacity', 1.0);
	});

	$(document).mouseup(function(event) {
		if (selecting_dates) {
			selecting_dates = false;
			State.sync(null, {'link': $("#dates li").filter(".activedate")});
		}
	});

	
});

// vim: noet ts=4
