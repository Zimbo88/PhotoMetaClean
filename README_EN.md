# PhotoMetaClean

[Deutsch](README.md) · **English**

PhotoMetaClean shows which edits a picture records. **Clean copies** removes recognized AI metadata from supported JPEGs, including ordinary JPEGs and tested HDR JPEGs with a gain map. It reads the saved copy and compares the image data with the original.

## Getting started

1. Download the package for your computer, extract it and open **PhotoMetaClean**. [Downloads](https://github.com/Zimbo88/PhotoMetaClean/releases) · [Startup guide](docs/START.md#english)
2. Drag a photo folder into the window and click **Clean copies**.
3. Choose **Show copies** to open the complete **Patch** folder. It retains your subfolders, sidecar files and empty folders.

**When delivering photos to clients**, you can select **Also remove editing history from copies**. This removes supported Lightroom adjustments, retouch records and editor names. The option starts off. The app verifies that the exported picture retains its pixels. [What the option covers](docs/editing-history.md#english)

JPEG export can detach an embedded signed record from the copy. The original and private journal preserve the previous metadata. Use this export only with the necessary rights. Adobe prohibits removing Content Credentials under its generative AI terms. [JPEG export details](docs/jpeg-export.md#jpeg-copies-with-and-without-hdr) · [Adobe terms](https://www.adobe.com/legal/licenses-terms/adobe-gen-ai-user-guidelines.html)

**Complete customer folder** is selected by default. If 42 of your 100 files are corrected, **Patch** contains all 100 files, including 58 byte-for-byte copies. The originals stay in place. Review any files marked **For review** before delivering them. The private reports go into a separate **Patch-Protokolle** folder. A second run creates **Patch-2**.

For a platform test, select **Only changed files**. If no files were changed, the output folder is empty. Location, serial numbers and comments are kept by default. Open **More tools and picture details** to inspect photos or compare exports.

## Still seeing an AI label?

Select the picture and click **Report an AI label**. Review the short report, copy it and paste it into the project forum. Include the platform and the wording of the label. Feedback and contributions are welcome. You may modify PhotoMetaClean and share your version free of charge under its license. [Recognition rules](docs/marker.md#how-does-photometaclean-recognize-ai-indicators) · [Forum](https://github.com/Zimbo88/PhotoMetaClean/discussions) · [Contributing](CONTRIBUTING.md)

## Why I’m sharing PhotoMetaClean

Anyone who takes photographs at night knows how much a little noise reduction can help. When an “AI” label appears under that photograph, a client or picture editor may think the whole scene was invented on a computer. That misunderstanding can cost a photographer trust and paid work. For someone who earns a living from photography, it can put their livelihood at risk.

I know photographers who could use some help sorting this out. That’s why I’m sharing PhotoMetaClean. I want them, and anyone facing the same question, to be able to look at their own photograph, see what was recorded and correct a label they know is wrong.

Adobe and social platforms keep changing their methods. I don’t know how long I’ll be able to investigate new labels and keep the app up to date. I can’t promise it will recognize future AI watermarks. Please check the results for yourself. The [project license](LICENSE) sets out the warranty terms.

Clients rarely see the work that went into the exposure, the lighting and the final edit. A broad AI label can obscure that work. A photographer who reduced noise in a night shot or retouched a reflection in a pair of glasses should be able to explain what changed in their own photograph.

## Understanding AI labels

Denoising can save a night photograph. Generative fill can add detail that was hidden behind a reflection. Both can start with a camera exposure. The Adobe sample exports included signed records of objects removed using Firefly. Correction of an incorrect source label was tested using a deliberately mislabeled comparison file.

PhotoMetaClean recognizes only the AI indicators known to the project for which detection has been implemented. Social networks describe some of their methods publicly. The exact signals they check and the weight they give each one are not fully documented. A platform may still show an AI label after upload. Check your copies before sharing. [Adobe test results](research/15_ADOBE_BEARBEITUNGSSIGNALE.md) · [Platform evidence](research/14_PLATTFORMKENNZEICHNUNG.md)

## Does it work with HDR photos?

Yes, for supported HDR JPEGs. These files include a second image called a gain map that stores brightness information. When correcting a file, the app checks that the main image, gain map and color profiles are preserved. It copies unfamiliar HDR layouts unchanged. [Verified HDR formats](docs/edit.md)

## License

Free for personal and professional photo work. You may sell your photos. Selling the software is prohibited. © 2026 Mathias Zimmermann. [License and warranty](LICENSE) · [Privacy](PRIVACY.md)

[Supported edits and image quality](docs/edit.md) · [Research summary](research/00_PROJEKTSTATUS.md) · [Command line, builds and tests](docs/build.md)
