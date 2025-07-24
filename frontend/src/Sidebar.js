import { Play, Search, Settings, User } from "lucide-react";
import Title from "./Title";

const Sidebar = ({ setActiveMenu, activeMenu }) => (
  <div className="w-64 bg-black text-white min-h-screen p-4 flex flex-col font-montserrat">
    <Title text="V_TRACK UI" />
    <ul>
      {[
        { name: "Chương trình", icon: <Play className="mr-2 text-blue-custom" /> },
        { name: "Truy vấn", icon: <Search className="mr-2 text-red-custom" /> },
        { name: "Cấu hình", icon: <Settings className="mr-2 text-gray-custom" /> },
        { name: "Tài khoản", icon: <User className="mr-2 text-yellow-custom" /> },
      ].map((item) => (
        <li
          key={item.name}
          className={`flex items-center p-3 hover:bg-gray-800 cursor-pointer transition duration-300 ${
            activeMenu === item.name ? "bg-gray-800" : ""
          }`}
          onClick={() => setActiveMenu(item.name)}
        >
          {item.icon} {item.name}
        </li>
      ))}
    </ul>
  </div>
);

export default Sidebar;