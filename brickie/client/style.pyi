from typing import TypeVar, Union

TStyle = TypeVar('TStyle', bound='Style')


class Style:
    def __init__(self, selector: str): ...

    def to_css(self, attr_selector=None) -> str: ...

    def __call__(
        self,
        align_content=None,
        align_items=None,
        align_self=None,
        all=None,
        azimuth=None,
        background=None,
        background_attachment=None,
        background_blend_mode=None,
        background_color=None,
        background_image=None,
        background_position=None,
        background_repeat=None,
        border=None,
        border_bottom=None,
        border_bottom_color=None,
        border_bottom_style=None,
        border_bottom_width=None,
        border_collapse=None,
        border_color=None,
        border_left=None,
        border_left_color=None,
        border_left_style=None,
        border_left_width=None,
        border_right=None,
        border_right_color=None,
        border_right_style=None,
        border_right_width=None,
        border_spacing=None,
        border_style=None,
        border_top=None,
        border_top_color=None,
        border_top_style=None,
        border_top_width=None,
        border_width=None,
        bottom=None,
        box_decoration_break=None,
        box_sizing=None,
        break_after=None,
        break_before=None,
        break_inside=None,
        caption_side=None,
        caret_color=None,
        clear=None,
        clip=None,
        color=None,
        column_count=None,
        column_fill=None,
        column_rule=None,
        column_rule_color=None,
        column_rule_style=None,
        column_rule_width=None,
        column_span=None,
        column_width=None,
        columns=None,
        contain=None,
        content=None,
        counter_increment=None,
        counter_reset=None,
        cue=None,
        cue_after=None,
        cue_before=None,
        cursor=None,
        direction=None,
        display=None,
        elevation=None,
        empty_cells=None,
        flex=None,
        flex_basis=None,
        flex_direction=None,
        flex_flow=None,
        flex_grow=None,
        flex_shrink=None,
        flex_wrap=None,
        float=None,
        font=None,
        font_family=None,
        font_feature_settings=None,
        font_kerning=None,
        font_size=None,
        font_size_adjust=None,
        font_stretch=None,
        font_style=None,
        font_synthesis=None,
        font_variant=None,
        font_variant_caps=None,
        font_variant_east_asian=None,
        font_variant_ligatures=None,
        font_variant_numeric=None,
        font_variant_position=None,
        font_weight=None,
        glyph_orientation_vertical=None,
        height=None,
        isolation=None,
        justify_content=None,
        left=None,
        letter_spacing=None,
        line_height=None,
        list_style=None,
        list_style_image=None,
        list_style_position=None,
        list_style_type=None,
        margin=None,
        margin_bottom=None,
        margin_left=None,
        margin_right=None,
        margin_top=None,
        max_height=None,
        max_width=None,
        min_height=None,
        min_width=None,
        mix_blend_mode=None,
        opacity=None,
        order=None,
        orphans=None,
        outline=None,
        outline_color=None,
        outline_offset=None,
        outline_style=None,
        outline_width=None,
        overflow=None,
        padding=None,
        padding_bottom=None,
        padding_left=None,
        padding_right=None,
        padding_top=None,
        page_break_after=None,
        page_break_before=None,
        page_break_inside=None,
        pause=None,
        pause_after=None,
        pause_before=None,
        pitch=None,
        pitch_range=None,
        play_during=None,
        position=None,
        quotes=None,
        resize=None,
        rest=None,
        rest_after=None,
        rest_before=None,
        richness=None,
        right=None,
        scroll_margin=None,
        scroll_margin_block=None,
        scroll_margin_block_end=None,
        scroll_margin_block_start=None,
        scroll_margin_bottom=None,
        scroll_margin_inline=None,
        scroll_margin_inline_end=None,
        scroll_margin_inline_start=None,
        scroll_margin_left=None,
        scroll_margin_right=None,
        scroll_margin_top=None,
        scroll_padding=None,
        scroll_padding_block=None,
        scroll_padding_block_end=None,
        scroll_padding_block_start=None,
        scroll_padding_bottom=None,
        scroll_padding_inline=None,
        scroll_padding_inline_end=None,
        scroll_padding_inline_start=None,
        scroll_padding_left=None,
        scroll_padding_right=None,
        scroll_padding_top=None,
        scroll_snap_align=None,
        scroll_snap_stop=None,
        scroll_snap_type=None,
        scrollbar_color=None,
        scrollbar_width=None,
        speak=None,
        speak_as=None,
        speak_header=None,
        speak_numeral=None,
        speak_punctuation=None,
        speech_rate=None,
        stress=None,
        table_layout=None,
        text_align=None,
        text_combine_upright=None,
        text_decoration=None,
        text_indent=None,
        text_orientation=None,
        text_overflow=None,
        text_transform=None,
        top=None,
        transform=None,
        transform_box=None,
        transform_origin=None,
        unicode_bidi=None,
        vertical_align=None,
        visibility=None,
        voice_balance=None,
        voice_duration=None,
        voice_family=None,
        voice_pitch=None,
        voice_range=None,
        voice_rate=None,
        voice_stress=None,
        voice_volume=None,
        volume=None,
        white_space=None,
        widows=None,
        width=None,
        word_spacing=None,
        writing_mode=None,
        z_index=None,
        **properties: Union[str, int, float]) -> TStyle: ...
