from . import agent as agnt

def main() -> None:
    m_agnt : agnt.Agent = agnt.Agent()
    m_agnt.run()

if __name__ == "__main__":
    main()