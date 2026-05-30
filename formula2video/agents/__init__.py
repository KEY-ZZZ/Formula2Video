"""Agent implementations for the Formula2Video pipeline.

Each agent is a small module exposing a ``run(...)`` function that consumes
upstream contracts and produces the next contract in the chain:

    Intent -> Curriculum -> Script -> SceneSpec -> Manim -> Assembly
"""
