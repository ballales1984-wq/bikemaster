"""Tests for aethermap.render.canvas (Phase 4 Canvas 2D fallback renderer)."""
from __future__ import annotations

import re

import pytest

from aethermap.render.canvas import render_canvas, render_canvas_html
from aethermap.render.camera import Camera
from aethermap.render.scene import Entity, Scene


class TestRenderCanvas:
    def test_returns_svg_string(self):
        scene = Scene.example()
        svg = render_canvas(scene)
        assert isinstance(svg, str)
        assert svg.startswith("<?xml")

    def test_svg_has_viewbox(self):
        scene = Scene.example()
        svg = render_canvas(scene, width=1024, height=768)
        assert 'width="1024"' in svg
        assert 'height="768"' in svg

    def test_svg_contains_globe_lines(self):
        scene = Scene.example()
        svg = render_canvas(scene)
        assert "<line " in svg
        assert 'stroke="rgb(60,90,130)"' in svg

    def test_svg_contains_entities(self):
        scene = Scene.example()
        svg = render_canvas(scene)
        assert "<circle " in svg or "<polyline " in svg

    def test_custom_bg_color(self):
        scene = Scene.example()
        svg = render_canvas(scene, bg=(20, 30, 40))
        assert '#141e28' in svg

    def test_empty_scene(self):
        scene = Scene()
        svg = render_canvas(scene)
        assert svg.startswith("<?xml")

    def test_grid_overlay(self):
        scene = Scene.example()
        svg_no_grid = render_canvas(scene, grid=False)
        svg_grid = render_canvas(scene, grid=True)
        assert svg_no_grid.count("polyline") < svg_grid.count("polyline")


class TestRenderCanvasHtml:
    def test_returns_html(self):
        scene = Scene.example()
        html = render_canvas_html(scene)
        assert html.startswith("<!doctype html>")
        assert "<svg" in html
        assert "</svg>" in html

    def test_html_has_hud(self):
        scene = Scene.example()
        html = render_canvas_html(scene)
        assert "AetherMap" in html
        assert "Canvas 2D fallback" in html

    def test_entity_count_in_hud(self):
        scene = Scene()
        scene.add(Entity(tipo="strada", kind="line", points=[], color=[0.5, 0.5, 0.5]))
        scene.add(Entity(tipo="albero", position=None, color=[0.3, 0.6, 0.3]))
        html = render_canvas_html(scene)
        assert "entities: 2" in html
