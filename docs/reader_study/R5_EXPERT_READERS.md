# R5 expert reader study: how to run it

**Pack:** 212 images (planned 216; only 32 Stable Diffusion control edits were available from distinct cases) from the main test set, each from a different case, stratified by source: 36 each of unedited
lesion images, LaMa erasures, LaMa control edits, unedited lesion-free images, Stable Diffusion erasures and Stable
Diffusion control edits (pre-registration: `docs/REVIEW_EXPERIMENTS.md`, R5 and Amendment 2).

**Readers:** at least two board-certified radiologists, 5 or more years after certification; a gastroenterologist or
endoscopist for colonoscopy if available. None may have seen packs 2 or 3 (the trainee rounds).

## Your steps (once, about 10 minutes)

1. Open notebook 49 in Colab, Runtime > Run all. Section 1 builds the pack and creates the Google Sheet
   "MedScope reader study - pack 4" in your Drive, then prints its link and the script to paste.
2. In the Sheet: Extensions > Apps Script, paste the script, Save; Deploy > New deployment > Web app; Execute as Me,
   access Anyone; Deploy; authorize. Copy the Web app URL (ends in `/exec`).
3. Paste the URL into ENDPOINT in section 2 and run it. It checks the connection, publishes the page and prints the
   TEST link and one personal link per reader.
4. Open the TEST link yourself and answer two or three images; check that rows appear in the Sheet's answers tab.
5. Send each reader their own link with the message below. Write each reader's name next to their code in the
   Sheet's readers tab (the page and the analysis never see names).
6. Run section 3 any time to see progress; run section 4 when everyone has finished. The report goes to
   `results/reader_study_experts.md` and a Google Doc.

## Message to readers (edit freely)

> Dear Dr ___,
>
> Thank you for agreeing to help with our image-reading study. It evaluates whether automatically edited medical
> images still show a finding, as part of a study on how AI models answer questions about medical images.
>
> Your personal link: ___
>
> - 212 images (CT, MRI, X-ray, ultrasound, colonoscopy) from public research datasets; no patient information.
> - Two quick questions per image: has the image been digitally edited, and the clinical question shown
>   (e.g. "Is there a polyp?"). Answer from the image alone.
> - About 2 hours in total, in as many sittings as you like. Every answer is saved automatically; you can close
>   the page and open the link again later, on any device, to continue where you stopped. Nothing needs to be sent back.
> - A computer or tablet works best for viewing the images.
>
> Please use only your own link, and do not discuss the images with other readers until everyone has finished.
> Questions: gurrambhaskar.ai@gmail.com
>
> With many thanks,
> Bhaskar Gurram

## Notes

- Readers are acknowledged, or included as co-authors if they meet the authorship criteria (substantial contribution,
  revising the manuscript, approving the final version).
- Some institutions ask that reader studies on public de-identified data be registered or declared exempt; check
  with the readers' institutions if needed.
- If a reader is offline when finishing, the page offers a backup file; put any such file in
  `MyDrive/medscope/reader/answers_pack4/` and section 4 includes it.
