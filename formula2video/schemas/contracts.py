"""Core data contracts for Formula2Video.

These Pydantic models are the *single source of truth* shared across all
agents. Upstream agents tag intent; downstream agents read only the fields
they own. The ``SceneSpec`` is the central enriched contract.

Field ownership (who reads what):
    manim.*, wait_after_s           -> Manim Agent (WP6)
    tts.*, narration_duration_s     -> TTS Agent (WP7)
    music_cue.*, pacing, insight    -> Music Agent (WP8)
    pixverse.*                      -> PixVerse Agent (WP9)
    timestamp_start_s               -> Assembly Agent (WP10)
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #
class VisualType(str, Enum):
    """How a beat is visually realised."""

    MANIM = "manim"
    PIXVERSE = "pixverse"
    HYBRID = "hybrid"


class Pacing(str, Enum):
    """Narration / animation pacing. Drives duration multipliers and music."""

    FAST = "fast"
    NORMAL = "normal"
    SLOW = "slow"


class CameraType(str, Enum):
    """Manim scene base class selector."""

    STATIC = "Scene"
    MOVING = "MovingCameraScene"
    THREE_D = "ThreeDScene"


# --------------------------------------------------------------------------- #
# WP1 - Intent
# --------------------------------------------------------------------------- #
class Intent(BaseModel):
    """Parsed user intent (output of Intent Agent)."""

    formula_latex: str = Field(..., description="The formula in LaTeX.")
    topic: str = Field("", description="Short topic description.")
    audience_level: str = Field("本科生", description="Target audience level.")
    learning_goal: str = Field("", description="What the viewer should grasp.")
    estimated_duration_s: float = Field(
        60.0, description="Rough target video duration in seconds."
    )


# --------------------------------------------------------------------------- #
# WP2 - Curriculum
# --------------------------------------------------------------------------- #
class InlinePrerequisite(BaseModel):
    """A single prerequisite explained inline in one sentence."""

    concept: str
    one_liner: str


class Curriculum(BaseModel):
    """Minimal-just-in-time curriculum (output of Curriculum Agent)."""

    core_concept: str = ""
    inline_prerequisites: List[InlinePrerequisite] = Field(default_factory=list)
    teaching_order: List[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# WP3 - Script
# --------------------------------------------------------------------------- #
class ScriptSegment(BaseModel):
    """One tagged narration segment."""

    narration: str
    visual_type: VisualType = VisualType.MANIM
    insight_moment: bool = False
    pacing: Pacing = Pacing.NORMAL
    pixverse_object: Optional[str] = Field(
        None,
        description="Photorealistic object description; only set for pixverse beats.",
    )


class Script(BaseModel):
    """Tagged script (output of Script Agent)."""

    segments: List[ScriptSegment] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# WP5 - Manim / PixVerse / TTS / Music sub-specs
# --------------------------------------------------------------------------- #
class ManimObject(BaseModel):
    """A drawable object inside a Manim scene."""

    id: str
    type: str = Field("Text", description="Manim mobject class, e.g. MathTex, Text.")
    content: str = ""
    color: Optional[str] = None


class ManimAction(BaseModel):
    """A single step in a Manim animation sequence."""

    action: str = Field(..., description="Animation name (Write/Create/...) or 'wait'.")
    target: Optional[str] = Field(None, description="Object id the action applies to.")
    run_time: float = 1.0
    duration: Optional[float] = Field(None, description="For 'wait' actions.")


class ManimSpec(BaseModel):
    """Executable spec for a single Manim scene."""

    scene_class: str
    camera_type: CameraType = CameraType.STATIC
    camera_action: Optional[str] = None
    objects: List[ManimObject] = Field(default_factory=list)
    animation_sequence: List[ManimAction] = Field(default_factory=list)


class PixVerseSpec(BaseModel):
    """Spec for a photorealistic PixVerse beat. Never contains text/formulas."""

    prompt: str = Field(..., description="Image/video generation prompt.")
    duration_s: float = 4.0
    motion: str = Field("subtle", description="High-level camera/subject motion.")


class TTSSpec(BaseModel):
    """Narration audio spec."""

    text: str
    pause_before_s: float = 0.3
    pause_after_s: float = 0.5


class MusicCue(BaseModel):
    """Music cue for a beat (read by Music Agent)."""

    type: str = Field("ambient", description="ambient / buildup / revelation / ...")
    transition: Optional[str] = None
    volume_relative: float = 0.2


# --------------------------------------------------------------------------- #
# WP5 - Scene Spec (the single source of truth)
# --------------------------------------------------------------------------- #
class SceneBeat(BaseModel):
    """One enriched scene beat."""

    scene_id: str
    timestamp_start_s: float = 0.0
    narration: str = ""
    narration_duration_s: float = 0.0

    pacing: Pacing = Pacing.NORMAL
    insight_moment: bool = False
    wait_after_s: float = 0.3

    visual_type: VisualType = VisualType.MANIM
    manim: Optional[ManimSpec] = None
    pixverse: Optional[PixVerseSpec] = None
    tts: Optional[TTSSpec] = None
    music_cue: Optional[MusicCue] = None


class SceneSpec(BaseModel):
    """The enriched scene spec - the contract every downstream agent reads."""

    beats: List[SceneBeat] = Field(default_factory=list)
    total_duration_s: float = 0.0

    def recompute_timeline(self) -> "SceneSpec":
        """Recompute ``timestamp_start_s`` for every beat and total duration.

        Each beat starts where the previous one ended. A beat's contribution
        to the timeline is its narration duration plus its trailing wait.
        """
        cursor = 0.0
        for beat in self.beats:
            beat.timestamp_start_s = round(cursor, 3)
            cursor += beat.narration_duration_s + beat.wait_after_s
        self.total_duration_s = round(cursor, 3)
        return self
