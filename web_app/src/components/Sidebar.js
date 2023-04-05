import React from "react";

const Sidebar = ({ items, onSelect }) => (
  <aside className="sidebar">
    <ul className="items-list">
      {items.map(item => (
        <li
          key={item.id}
          className="item"
          onClick={() => onSelect(item)}
        >
          {item.content.url}
        </li>
      ))}
    </ul>
  </aside>
);

export default Sidebar;