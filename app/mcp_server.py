import datetime
import os
import logging
from mcp.server.fastmcp import FastMCP

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("eduguide-mcp-server")

# Initialize FastMCP Server
mcp = FastMCP("EduGuide MCP Server")

@mcp.tool()
def search_internet_resources(query: str) -> str:
    """Use this to find free educational resources (textbooks, videos, online courses).
    
    Args:
        query: The search query (e.g., 'free physics textbooks' or 'khan academy algebra').
        
    Returns:
        A list of free educational resource links and descriptions.
    """
    logger.info(f"mcp tool search_internet_resources called with query: {query}")
    
    # Simulated database of free resources
    resources = {
        "math": [
            "[Khan Academy Algebra 1](https://www.khanacademy.org/math/algebra) - Free tutorials and exercises",
            "[OpenStax Precalculus Textbook](https://openstax.org/details/books/precalculus) - Free peer-reviewed PDF textbook",
            "[MIT OCW Linear Algebra](https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/) - Free lecture videos and syllabus"
        ],
        "physics": [
            "[OpenStax Physics Textbook](https://openstax.org/details/books/college-physics) - Free college-level physics textbook",
            "[CrashCourse Physics](https://www.youtube.com/playlist?list=PL8dPuuaLjXtN0ge7yD5RY3Co9YOpBh3ns) - Fun and fast educational video series",
            "[PhET Interactive Simulations](https://phet.colorado.edu/) - Free interactive science and math simulations"
        ],
        "chemistry": [
            "[OpenStax Chemistry 2e](https://openstax.org/details/books/chemistry-2e) - Free peer-reviewed chemistry textbook",
            "[CrashCourse Chemistry](https://www.youtube.com/playlist?list=PL8dPuuaLjXtPHzzYuWy6fYEaX9mQQ8oGr) - Video lecture playlist for chemistry concepts"
        ],
        "computer science": [
            "[CS50 Introduction to Computer Science](https://www.edx.org/course/introduction-computer-science-harvardx-cs50x) - Harvard's famous introductory programming course",
            "[Python for Everybody](https://www.py4e.com/) - Free interactive book and videos to learn Python programming"
        ],
        "biology": [
            "[OpenStax Biology 2e](https://openstax.org/details/books/biology-2e) - Free peer-reviewed biology textbook",
            "[Khan Academy Biology](https://www.khanacademy.org/science/biology) - High school and AP biology video courses"
        ]
    }
    
    query_lower = query.lower()
    found = []
    for category, links in resources.items():
        if category in query_lower:
            found.extend(links)
            
    if not found:
        return (
            "No specific resource matched your exact topic, but here are general free educational platforms:\n"
            "1. [Khan Academy](https://www.khanacademy.org) - Lessons on math, science, history, and grammar.\n"
            "2. [OpenStax](https://openstax.org) - Peer-reviewed, open-licensed textbooks.\n"
            "3. [MIT OpenCourseWare](https://ocw.mit.edu) - Course materials for almost all of MIT's subjects."
        )
        
    return "Here are the top free educational resources found:\n" + "\n".join(f"- {link}" for link in found)

@mcp.tool()
def get_current_calendar() -> str:
    """Returns the current date and time. Use this when planning a study schedule relative to today.
    
    Returns:
        The current date formatted as YYYY-MM-DD.
    """
    logger.info("mcp tool get_current_calendar called")
    now = datetime.datetime.now()
    return f"Today is {now.strftime('%A, %B %d, %Y')}."

@mcp.tool()
def log_study_schedule(student_name: str, schedule_details: str) -> str:
    """Saves or exports the finalized study schedule to the student's records/file.
    
    Args:
        student_name: Name of the student or identifier (e.g. 'Jane').
        schedule_details: The formatted study schedule to log.
        
    Returns:
        Confirmation message that the schedule has been saved.
    """
    logger.info(f"mcp tool log_study_schedule called for student: {student_name}")
    filename = f"{student_name.lower().replace(' ', '_')}_study_schedule.txt"
    try:
        # Write to the project root directory
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filepath = os.path.join(project_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"STUDY SCHEDULE FOR: {student_name}\n")
            f.write(f"LOGGED ON: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*40 + "\n\n")
            f.write(schedule_details)
            
        logger.info(f"Study schedule saved successfully to: {filepath}")
        return f"Success: Study schedule saved to local file {filename}."
    except Exception as e:
        logger.error(f"Error saving study schedule: {str(e)}")
        return f"Error saving schedule: {str(e)}"

if __name__ == "__main__":
    mcp.run()
