import ImageInspector from "./ImageInspector";
import VideoInspector from "./VideoInspector";
import PdfInspector from "./PdfInspector";
import AudioInspector from "./AudioInspector";
import EmbedInspector from "./EmbedInspector";
import ScormInspector from "./ScormInspector";
import AssignmentInspector from "./AssignmentInspector";
import QuizInspector from "./QuizInspector";

export const inspectorRegistry = {
  image: ImageInspector,
  video: VideoInspector,
  pdf: PdfInspector,
  audio: AudioInspector,
  embed: EmbedInspector,
  scorm: ScormInspector,
  assignment: AssignmentInspector,
  quiz_reference: QuizInspector,
};
