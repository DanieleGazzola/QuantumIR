#include "slang/ast/Compilation.h"
#include "slang/driver/Driver.h"
#include "slang/util/VersionInfo.h"
#include "slang/ast/ASTSerializer.h"
#include "slang/text/Json.h"
#include "slang/ast/symbols/CompilationUnitSymbols.h"

#include <iostream>
#include <fstream>
#include <string>

using namespace slang;
using namespace slang::driver;
using namespace slang::ast;

int main(int argc, char** argv) {

    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <filename>" << std::endl;
        return 1;
    }

    // Convert the filename from argv[1] to a std::string
    std::string fullPath = argv[1];

    // Find the position of the last slash
    size_t lastSlashPos = fullPath.find_last_of("/\\");
    std::string filename;
    
    if (lastSlashPos != std::string::npos) {
        // Extract the filename following the last slash
        filename = fullPath.substr(lastSlashPos + 1);
    } else {
        // If no slash is found, the entire string is the filename
        filename = fullPath;
    }

    std::cout << "Chosen Verilog input file: " << filename << "\n" <<std::endl;

    std::ofstream file;
    file.open("output.json");

    Driver driver;
    driver.addStandardArgs();

    std::optional<bool> showHelp;
    std::optional<bool> showVersion;
    driver.cmdLine.add("-h,--help", showHelp, "Display available options");
    driver.cmdLine.add("--version", showVersion, "Display version information and exit");

    if (!driver.parseCommandLine(argc, argv))
        return 1;

    if (showHelp == true) {
        printf("%s\n", driver.cmdLine.getHelpText("slang SystemVerilog compiler").c_str());
        return 0;
    }

    if (showVersion == true) {
        printf("slang version %d.%d.%d+%s\n", VersionInfo::getMajor(),
            VersionInfo::getMinor(), VersionInfo::getPatch(),
            std::string(VersionInfo::getHash()).c_str());
        return 0;
    }

    if (!driver.processOptions())
        return 2;

    bool ok = driver.parseAllSources();

    auto compilation = driver.createCompilation();
    ok &= driver.reportCompilation(*compilation, /* quiet */ false);
    
    JsonWriter writer;
    writer.setPrettyPrint(true);

    ASTSerializer serializer(*compilation, writer);
    serializer.serialize(compilation->getRoot());

    file << writer.view().data();

    file.close();

    return ok ? 0 : 3;
}