import Sidebar from "./Sidebar";
import VtrackConfig from "./VtrackConfig";
import QueryComponent from "./QueryComponent";
import Account from "./Account";
import ProgramTab from "./components/program/ProgramTab";
import useProgramLogic from "./hooks/useProgramLogic";

const Dashboard = ({ setActiveMenu, activeMenu, authState, onLogout }) => {
  const {
    runningCard,
    fileList,
    customPath,
    showConfirmButton,
    firstRunCompleted,
    handleRunStop,
    handleConfirmRun,
    isRunning,
    setCustomPath,
  } = useProgramLogic();

  return (
    <div className="flex min-h-screen bg-gray-900 text-white font-montserrat">
      <Sidebar setActiveMenu={setActiveMenu} activeMenu={activeMenu} />
      <div className="flex-1 p-6 w-full">
        {activeMenu === "Chương trình" ? (
          <ProgramTab
            runningCard={runningCard}
            fileList={fileList}
            customPath={customPath}
            showConfirmButton={showConfirmButton}
            firstRunCompleted={firstRunCompleted}
            handleRunStop={handleRunStop}
            handleConfirmRun={handleConfirmRun}
            isRunning={isRunning}
            setCustomPath={setCustomPath}
          />
        ) : activeMenu === "Cấu hình" ? (
          <VtrackConfig />
        ) : activeMenu === "Truy vấn" ? (
          <QueryComponent />
        ) : activeMenu === "Tài khoản" ? (
          <Account authState={authState} onLogout={onLogout} />
        ) : (
          <div>
            <h1 className="text-3xl font-bold">Đang phát triển: {activeMenu}</h1>
            <p>Nội dung cho {activeMenu} sẽ được thêm sau.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;