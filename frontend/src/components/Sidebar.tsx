// src/components/Sidebar.tsx
export default function Sidebar() {
    return (
      <aside id="sidebar" aria-label="Departments (Demo)">
        <h3>Departments</h3>
        <div className="side-section" id="deptList">
          {[
            { t:"ECS Dean’s Office", sub:"Riverside Hall — 2nd Floor", meta:"Hours: Mon–Fri 8:00–5:00" },
            { t:"College of Business Dean’s Office", sub:"Tahoe Hall — 1st Floor", meta:"Hours: Mon–Fri 8:00–5:00" },
            { t:"NSM Dean’s Office", sub:"Sequoia Hall — 1st Floor", meta:"Hours: Mon–Fri 8:00–5:00" },
            { t:"Arts & Letters Dean’s Office", sub:"Mendocino Hall — 1st Floor", meta:"Hours: Mon–Fri 8:00–5:00" },
          ].map((d,i)=>(
            <div className="side-item" key={i}>
              <div className="title">{d.t}</div>
              <div className="sub">{d.sub}</div>
              <div className="meta">{d.meta}</div>
            </div>
          ))}
        </div>
      </aside>
    );
  }
  