import torch, torch.nn as nn, torch.nn.functional as F
class SRVGGNetCompact(nn.Module):
    def __init__(s, num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=32, upscale=4):
        super().__init__(); s.upscale = upscale
        s.body = nn.ModuleList([nn.Conv2d(num_in_ch, num_feat, 3, 1, 1), nn.PReLU(num_parameters=num_feat)])
        for _ in range(num_conv):
            s.body.append(nn.Conv2d(num_feat, num_feat, 3, 1, 1)); s.body.append(nn.PReLU(num_parameters=num_feat))
        s.body.append(nn.Conv2d(num_feat, num_out_ch * upscale * upscale, 3, 1, 1))
        s.upsampler = nn.PixelShuffle(upscale)
    def forward(s, x):
        out = x
        for m in s.body: out = m(out)
        out = s.upsampler(out)
        return out + F.interpolate(x, scale_factor=s.upscale, mode='nearest')
def load(path_a, path_b=None, dni=0.5):
    m = SRVGGNetCompact()
    a = torch.load(path_a, map_location='cpu'); a = a.get('params', a)
    if path_b:
        b = torch.load(path_b, map_location='cpu'); b = b.get('params', b)
        a = {k: dni * a[k] + (1 - dni) * b[k] for k in a}
    m.load_state_dict(a); m.eval(); return m
