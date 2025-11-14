// src/components/Resources.tsx
const resources = [
    {
      title: "ASI Food Pantry",
      hours: "Mon–Fri, 10:00 AM – 4:00 PM",
      where: "University Union (1st Floor)",
      url: "https://asi.csus.edu/asi-food-pantry/",
    },
    {
      title: "Student Health & Counseling",
      hours: "Mon–Fri, 8:00 AM – 5:00 PM",
      where: "Student Health Center",
      url: "https://www.csus.edu/student-life/health-counseling/",
    },
    {
      title: "Academic Advising",
      hours: "Mon–Fri, 9:00 AM – 4:30 PM",
      where: "Lassen Hall",
      url: "https://www.csus.edu/student-life/academic-advising/",
    },
    {
      title: "STEM Success Center",
      hours: "Mon–Fri, 9:00 AM – 5:00 PM",
      where: "Riverside Hall — Room 2010",
      url: "https://www.csus.edu/college/natural-sciences-mathematics/student-success-center.html",
    },
    {
      title: "Carlsen Center for Innovation & Entrepreneurship",
      hours: "Mon–Fri, 8:30 AM – 5:00 PM",
      where: "University Library — Lower Level",
      url: "https://carlsencenterforinnovation.org/",
    },
  ];
  
  
  export default function Resources() {
    return (
      <div className="res">
        {resources.map((r, i) => (
          <div className="res-item" key={i}>
            <div className="res-title">{r.title}</div>
            <div className="res-meta">
              <span className="chip">⏰ {r.hours}</span>
              <span className="chip">📍 {r.where}</span>
            </div>
            <div className="res-foot">
              More info: <a href={r.url} target="_blank" rel="noopener">official page ↗</a>
            </div>
          </div>
        ))}
      </div>
    );
  }
  