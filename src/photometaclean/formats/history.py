"""Editing records that can be removed from a rendered JPEG without touching display metadata."""
import re

HISTORY = "XMP:EditingHistory"
JPEG_EXTENSIONS = {".jpeg", ".jpg", ".jfif", ".jpe"}
HISTORY_RASTERS = {".png", ".apng", ".webp", ".tif", ".tiff", ".heic", ".heif", ".hif", ".avif"}
CRS = "http://ns.adobe.com/camera-raw-settings/1.0/"
XAP = "http://ns.adobe.com/xap/1.0/"
MM = "http://ns.adobe.com/xap/1.0/mm/"
PS = "http://ns.adobe.com/photoshop/1.0/"
TIFF = "http://ns.adobe.com/tiff/1.0/"
NS = {"XMP-crs": CRS, "XMP-xmp": XAP, "XMP-xmpMM": MM, "XMP-photoshop": PS, "XMP-tiff": TIFF}
EDITOR = re.compile(r"\b(?:Photoshop|Lightroom|Camera Raw|Affinity Photo|GIMP|darktable|RawTherapee|"
                    r"Capture One|ON1 Photo RAW|DxO PhotoLab|Snapseed|Pixelmator|Luminar|PaintShop Pro)\b", re.I)

# Keep the HDR/SDR rendering parameters, camera profiles and all unrecognized namespaces.
# These names refer to development instructions in already rendered JPEGs.
ADJUSTMENTS = frozenset("""
Version CompatibleVersion ProcessVersion WhiteBalance ColorTemperature Temperature Tint
Exposure Exposure2012 Contrast Contrast2012 Highlights2012 Shadows2012 Whites2012 Blacks2012
Brightness Shadows FillLight Recovery HighlightRecovery Blacks Texture Clarity Clarity2012
Dehaze Vibrance Saturation Sharpness LuminanceSmoothing AutoLateralCA ReshapeAmount Glow
ShadowTint RedHue RedSaturation GreenHue GreenSaturation BlueHue BlueSaturation
AllowFilters HasSettings HasCrop AlreadyApplied PointColors ColorVariance
RetouchAreas RetouchInfo MaskGroupBasedCorrections PaintBasedCorrections GradientBasedCorrections
CircularGradientBasedCorrections LensBlur AutoToneDigest AutoToneDigestNoSat
OverrideLookVignette LensManualDistortionAmount LensProfileEnable ConvertToGrayscale
""".split())
FAMILIES = ("Parametric", "Sharpen", "ColorNoiseReduction", "LuminanceNoiseReduction", "HueAdjustment",
            "SaturationAdjustment", "LuminanceAdjustment", "SplitToning", "ColorGrade", "Defringe",
            "Perspective", "Vignette", "PostCropVignette", "Grain", "ToneCurve", "Crop", "GrayMixer")


def history_field(tag, value):
    uri, name = tag
    if uri == CRS and (name in ADJUSTMENTS or name.startswith(FAMILIES)):
        return "crs:" + name
    if uri == MM and name in {"History", "Versions"}:
        return "xmpMM:" + name
    if uri == PS and name == "History":
        return "photoshop:History"
    if (uri, name) in {(XAP, "CreatorTool"), (TIFF, "Software")} and EDITOR.search(str(value)):
        return name
    return None


def history_fields(metadata):
    fields = set()
    for key, value in metadata.items():
        group, _, name = key.partition(":")
        name = name.rsplit(":", 1)[-1]
        if group in {"IFD0", "PNG"} and name == "Software" and EDITOR.search(str(value)):
            fields.add(group + ":Software")
        elif group in NS and history_field((NS[group], name), value):
            fields.add(group + ":" + name)
    return fields


def signed_edit(analysis):
    """Only explicitly declared operations in the active manifest qualify."""
    store = analysis.get("manifest") or {}
    active = store.get("manifests", {}).get(store.get("active_manifest"), {})
    operations = {"c2pa.edited", "c2pa.cropped", "c2pa.resized", "c2pa.filtered",
                  "c2pa.color_adjustments", "c2pa.transcoded", "c2pa.watermarked",
                  "c2pa.drawing", "c2pa.placed", "c2pa.converted", "c2pa.repackaged"}
    return any(action.get("action") in operations
               for assertion in active.get("assertions", ())
               if assertion.get("label", "").split(".v")[0] == "c2pa.actions"
               for action in assertion.get("data", {}).get("actions", ()) if isinstance(action, dict))
