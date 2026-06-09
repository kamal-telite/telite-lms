import React, { useState, useEffect } from 'react';
import QuestionRenderer from './QuestionRenderer';

const QuizPlayer = ({ quizId, attemptId, onComplete }) => {
  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [timeLeft, setTimeLeft] = useState(3600); // 1 hour mock
  
  useEffect(() => {
    const timer = setInterval(() => setTimeLeft(t => t > 0 ? t - 1 : 0), 1000);
    return () => clearInterval(timer);
  }, []);

  const handleAutosave = (questionId, answer) => {
    setAnswers(prev => ({ ...prev, [questionId]: answer }));
    // API mock: PUT /quiz-execution/attempts/{attemptId}/answers
    console.log(`Autosaved answer for ${questionId}:`, answer);
  };

  const handleSubmit = async () => {
    // API mock: POST /quiz-execution/attempts/{attemptId}/submit
    console.log('Quiz submitted', answers);
    onComplete();
  };

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white rounded-xl shadow-lg border border-slate-200">
      <div className="flex justify-between items-center mb-8 pb-4 border-b">
        <h2 className="text-2xl font-bold text-slate-800">Quiz Player</h2>
        <div className="px-4 py-2 bg-indigo-50 text-indigo-700 font-mono rounded-lg">
          Time Remaining: {Math.floor(timeLeft / 60)}:{String(timeLeft % 60).padStart(2, '0')}
        </div>
      </div>
      
      <div className="min-h-[400px]">
        {/* Placeholder for QuestionRenderer */}
        <QuestionRenderer 
          question={{ id: 1, type: 'multiple_choice', text: 'Sample Question?' }}
          currentAnswer={answers[1]}
          onChange={(ans) => handleAutosave(1, ans)}
        />
      </div>

      <div className="flex justify-between items-center mt-8 pt-6 border-t">
        <button 
          className="px-6 py-2 bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 transition-colors"
          onClick={() => setCurrentIndex(c => Math.max(0, c - 1))}
        >
          Previous
        </button>
        <span className="text-slate-500 font-medium">Question {currentIndex + 1} of {questions.length || 1}</span>
        <div className="space-x-3">
          <button 
            className="px-6 py-2 bg-indigo-50 text-indigo-700 rounded-lg hover:bg-indigo-100 transition-colors"
            onClick={() => setCurrentIndex(c => c + 1)}
          >
            Next
          </button>
          <button 
            onClick={handleSubmit}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors shadow-sm"
          >
            Submit Quiz
          </button>
        </div>
      </div>
    </div>
  );
};

export default QuizPlayer;
