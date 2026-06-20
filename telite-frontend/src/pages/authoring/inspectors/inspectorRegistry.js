import ImageInspector from "./ImageInspector";
import VideoInspector from "./VideoInspector";
import PdfInspector from "./PdfInspector";
import AudioInspector from "./AudioInspector";
import EmbedInspector from "./EmbedInspector";
import ScormInspector from "./ScormInspector";
import H5PInspector from "./H5PInspector";
import AssignmentInspector from "./AssignmentInspector";
import QuizInspector from "./QuizInspector";

export const inspectorRegistry = {
  image: ImageInspector,
  video: VideoInspector,
  pdf: PdfInspector,
  audio: AudioInspector,
  embed: EmbedInspector,
  scorm: ScormInspector,
  h5p: H5PInspector,
  assignment: AssignmentInspector,
  quiz: QuizInspector,
  quiz_reference: QuizInspector,
};
