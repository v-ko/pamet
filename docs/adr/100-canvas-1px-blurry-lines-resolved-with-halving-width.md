# Canvas: 1px blurry lines resolved by halving width

**Status:** accepted; implemented.

- Blurry lines - the problem is that with scaling 1px width lines inevitably take up non-integer pixel counts, and non-filled pixels are filled with reduced color values, which produces the blur...devising an ML strategy for adapting the zoom path and quantization to optimal values would be optimal. But i just reduced border size to 0.5 canvas units so the effect looks more uniform and that looks good for now :d
	- Quantization solution - we move the line to take up 2 pixels instead of 3 (or 1 instead of 2) by adjusting the coordinates. OR we adjust the line width (or both) (qt does something similar. lines seem to jitter)
	- Scale factor - zoom to scales that produce integer widths

The implemented choice is [`NOTE_BORDER_WIDTH = 0.5`](../../web-app/src/app/constants.ts), which scales with zoom; the alternatives above are not implemented.
