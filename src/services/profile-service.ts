import { mockApiResponse } from "@/services/mock-api";

export interface ListeningStatistic {
  id: string;
  label: string;
  value: string;
  detail: string;
}

const LISTENING_STATISTICS: ListeningStatistic[] = [
  {
    id: "listening-time",
    label: "कुल श्रवण",
    value: "४२ घण्टा",
    detail: "पछिल्लो ३० दिनमा ८ घण्टा",
  },
  {
    id: "completed",
    label: "पूरा रचना",
    value: "६८",
    detail: "कथा र कविता सबैभन्दा धेरै",
  },
  {
    id: "favorite-genre",
    label: "प्रिय विधा",
    value: "कविता",
    detail: "कुल श्रवणको ३८%",
  },
  {
    id: "listening-streak",
    label: "निरन्तरता",
    value: "१२ दिन",
    detail: "व्यक्तिगत उत्कृष्ट: १९ दिन",
  },
];

export async function getListeningStatistics() {
  return mockApiResponse(LISTENING_STATISTICS);
}
