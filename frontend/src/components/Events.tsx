// src/components/Events.tsx
export default function Events() {
    const events = [
      {
        title: "Global Entrepreneurship Week (GEW): Fund Your Research & Innovation Through Grants",
        when: "Mon, Nov 17, 10:00 – 11:30 AM",
        where: "University Union — Orchard Suite",
      },
      {
        title: "Hackathon Kickoff: Innovate for Sustainability",
        when: "Fri, Nov 14, 10:00 AM",
        where: "Carlsen Center — University Library",
      },
      {
        title: "Career Fair: Tech & Engineering",
        when: "Fri, Nov 14, 11:00 AM – 3:00 PM",
        where: "University Union Ballroom",
      },
      {
        title: "Women in CS Meetup",
        when: "Fri, Nov 14, 6:00 PM",
        where: "Riverside Hall Lobby",
      },
      {
        title: "Faculty Recital: STEM Meets the Arts",
        when: "Sat, Nov 15, 7:00 – 8:30 PM",
        where: "Music Recital Hall",
      },
      {
        title: "Committee on Diversity & Equity in STEM",
        when: "Mon, Nov 17, 1:30 – 3:00 PM",
        where: "Sequoia Hall — Room 120",
      },
    ];
  
    return (
      <div>
        {events.map((ev, i) => (
          <div className="event" key={i}>
            <div className="event-title">{ev.title}</div>
            <div className="event-row">
              <span className="badge">🗓️ {ev.when}</span>
              <span className="loc">📍 {ev.where}</span>
            </div>
          </div>
        ))}
      </div>
    );
  }
  