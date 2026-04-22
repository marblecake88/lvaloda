import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useEdgeBackSwipe } from "./hooks/useEdgeBackSwipe";
import { haptic } from "./tg";
import Home from "./screens/Home";
import ScenarioPicker from "./screens/ScenarioPicker";
import Chat from "./screens/Chat";
import Exam from "./screens/Exam";
import Prep from "./screens/Prep";
import Reflection from "./screens/Reflection";
import Vocabulary from "./screens/Vocabulary";
import Stats from "./screens/Stats";
import Shadowing from "./screens/Shadowing";
import Picture from "./screens/Picture";
import ShadowingPicker from "./screens/ShadowingPicker";
import Phrases, { PhraseDrill } from "./screens/Phrases";
import Reading from "./screens/Reading";
import ReadingPicker from "./screens/ReadingPicker";
import Translate from "./screens/Translate";

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();

  // Edge-swipe-from-left → back. Disabled on Home so it can't try to
  // pop past the entry route (would be a no-op anyway).
  useEdgeBackSwipe(
    () => {
      haptic("soft");
      navigate(-1);
    },
    { enabled: location.pathname !== "/" },
  );

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/chat" element={<ScenarioPicker initialTab="daily" />} />
      <Route path="/chat/:scenarioKey" element={<Chat mode="dialog" />} />
      <Route path="/exam" element={<ScenarioPicker initialTab="exam" />} />
      <Route path="/exam/prep/:topicKey" element={<Prep />} />
      <Route path="/exam/:topicKey" element={<Exam />} />
      <Route path="/reflection/:sessionId" element={<Reflection />} />
      <Route path="/vocabulary" element={<Vocabulary />} />
      <Route path="/stats" element={<Stats />} />
      <Route path="/shadowing" element={<ShadowingPicker />} />
      <Route path="/shadowing/:topicKey" element={<Shadowing />} />
      <Route path="/picture" element={<Picture />} />
      <Route path="/phrases" element={<Phrases />} />
      <Route path="/phrases/:category" element={<PhraseDrill />} />
      <Route path="/reading" element={<ReadingPicker />} />
      <Route path="/reading/:textId" element={<Reading />} />
      <Route path="/translate" element={<Translate />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
